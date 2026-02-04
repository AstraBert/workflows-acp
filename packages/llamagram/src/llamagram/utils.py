import functools
import json
import logging
import os
from pathlib import Path
from typing import cast

import aiofiles
from dotenv import load_dotenv
from mcp_use.client.task_managers.base import asyncio
from random_name import generate_name
from telegram import Document, File, User
from telegram.ext import CallbackContext
from workflows.events import Event
from workflows_acp.constants import AGENTFS_FILE, AVAILABLE_MODELS, DEFAULT_MODEL
from workflows_acp.events import (
    InputEvent,
    OutputEvent,
    PromptEvent,
    ThinkingEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from workflows_acp.llm_wrapper import LLMWrapper
from workflows_acp.tools.agentfs import configure_agentfs, load_all_files
from workflows_acp.workflow import AgentWorkflow

from .constants import (
    AGENT_TASK,
    DATA_DIR,
    DEFAULT_TO_AVOID,
    DEFAULT_TO_AVOID_FILES,
    SPECIAL_CHARS,
)
from .tools import TOOLS


def start(user: User | None) -> str:
    greetings = "Hello there, Llama Enthusiast!"
    if user is not None and user.username is not None:
        username = user.username
        if not username.startswith("@"):
            username = "@" + username
        greetings = f"Hello there, {username}!"

    return f"""
{greetings}
I am LlamaGram, your personal assistant for whatever concerns documents.
I can navigate the filesystem from the directory where you deployed me, and perform operations based on your text messages.
You can also upload PDF documents from this chat, that I will download and will be able to use afterwards.
With this being said, please, ask any questions you like!
    """


@functools.lru_cache(maxsize=1)
def get_llm() -> LLMWrapper:
    load_dotenv()
    llm_provider = os.getenv("LLAMAGRAM_LLM_PROVIDER", "openai")
    if llm_provider not in ("openai", "google", "anthropic"):
        raise ValueError(f"Unsupported model provider: {llm_provider}")
    model = os.getenv("LLAMAGRAM_LLM_MODEL", DEFAULT_MODEL[llm_provider])
    if AVAILABLE_MODELS.get(model) != llm_provider:
        raise ValueError(f"Unsupported model for provider {llm_provider}: {model}")
    api_key = os.getenv("LLAMAGRAM_LLM_API_KEY") or os.getenv(
        f"{llm_provider.upper()}_API_KEY"
    )
    if api_key is not None:
        redacted_api_key = api_key[:3] + "x" * (len(api_key) - 6) + api_key[-3:]
        logging.info(
            f"Starting the bot with {llm_provider.capitalize()} as LLM provider, {model} as LLM model and {redacted_api_key} as API key"
        )
    return LLMWrapper(
        tools=TOOLS,
        api_key=api_key,
        model=model,
        llm_provider=llm_provider,
        agent_task=AGENT_TASK,
    )


@functools.lru_cache(maxsize=1)
def get_workflow() -> AgentWorkflow:
    llm = get_llm()
    return AgentWorkflow(llm=llm, mcp_client=None, timeout=600)


def _get_file_name(document: Document) -> str:
    if document.file_name is None:
        return generate_name() + ".pdf"
    else:
        if document.file_name.endswith(".pdf"):
            return document.file_name
        return document.file_name + ".pdf"


async def _download_file_to_agentfs(file_path: str, content: bytes) -> str:
    file_path = str(Path(file_path).resolve())
    agentfs = await configure_agentfs()
    try:
        await agentfs.fs.write_file(file_path, content=content, encoding="utf-8")
    except Exception as e:
        return f"There was an error while writing the file: {e}"
    return "File written with success"


async def handle_documents(document: Document, context: CallbackContext) -> str:
    name = _get_file_name(document=document)
    path = os.path.join(DATA_DIR, name)
    try:
        fl = cast(File, await context.bot.get_file(document.file_id))
        ba = await fl.download_as_bytearray()
        await _download_file_to_agentfs(path, bytes(ba))
    except Exception as e:
        logging.error(str(e))
        return "There was an error while downloading your file, please try re-uploading"
    return f"Your file has been successfully downloaded at: {path}. Use this path to reference the file in your follow-up requests to the agent"


def _event_to_log(event: Event) -> str | None:
    if isinstance(event, ThinkingEvent):
        message = f"**Thought**: {event.content}"
        logging.info(message)
        return message
    elif isinstance(event, PromptEvent):
        message = f"**Observation**: {event.prompt}"
        logging.info(message)
        return message
    elif isinstance(event, ToolCallEvent):
        message = f"Calling tool **{event.tool_name}** with input:\n\n```json\n{json.dumps(event.tool_input, indent=2)}\n```"
        logging.info(message)
        return message
    elif isinstance(event, ToolResultEvent):
        message = f"Result for tool **{event.tool_name}**: {event.result}"
        logging.info(message)
        return message
    elif isinstance(event, OutputEvent):
        if event.final_output is not None:
            message = f"**Final response**: {event.final_output}"
            logging.info(message)
            return message
        message = f"**Error**: {event.error}"
        logging.error(message)
        return message
    return None


async def handle_prompt(text: str) -> tuple[str, str]:
    workflow = get_workflow()
    input_event = InputEvent(prompt=text, mode="bypass")
    handler = workflow.run(start_event=input_event)
    report = ""
    async for event in handler.stream_events():
        log = _event_to_log(event)
        if log is not None:
            report += log + "\n"
    result = await handler
    log = _event_to_log(result)
    if log is not None:
        report += log + "\n"
    return report, log or "No final response"


async def _write_temporary_report_file(content: str) -> str:
    path = "session-" + generate_name() + "-report.md"
    async with aiofiles.open(path, "w") as f:
        await f.write(content)
    return path


async def _remove_temporary_report_file(path: str) -> None:
    try:
        await asyncio.to_thread(os.remove, path)
    except Exception:
        pass


async def _setup_agentfs() -> None:
    if not AGENTFS_FILE.exists():
        logging.info("Loading all files in the current working directory to AgentFS")
        await load_all_files(DEFAULT_TO_AVOID, DEFAULT_TO_AVOID_FILES, progress=True)
        logging.info(
            "Finished loading all files in the current working directory to AgentFS"
        )
    else:
        logging.info(
            f"Detected {str(AGENTFS_FILE)} in current working directory, will not load files."
        )


def _escape_markdow_for_tg(markdown: str) -> str:
    for char in SPECIAL_CHARS:
        markdown = markdown.replace(char, f"\\{char}")
    return markdown
