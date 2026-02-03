import json
import logging
import os
from pathlib import Path
from typing import cast

from random_name import generate_name
from telegram import Document, File
from telegram.ext import CallbackContext
from workflows.events import Event
from workflows_acp.constants import AGENTFS_FILE
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

from .constants import AGENT_TASK, DATA_DIR, DEFAULT_TO_AVOID, DEFAULT_TO_AVOID_FILES
from .tools import TOOLS

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def start() -> str:
    return "Hey there! I am LlamaGram, your virtual assistant for summarizing and extracting knowledge from research papers - you simply need to upload them to this chat and let the magic happen!"


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
    if not DATA_DIR.is_dir():
        os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, name)
    try:
        fl = cast(File, await context.bot.get_file(document.file_id))
        ba = await fl.download_as_bytearray()
        await _download_file_to_agentfs(path, bytes(ba))
    except Exception as e:
        logging.error(str(e))
        return "There was an error while downloading your file, please try re-uploading"
    return f"Your file has been successfully downloaded at: {path}. Use this path to reference the file in your follow-up requests to the agent"


LLM = LLMWrapper(
    tools=TOOLS,
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4.1",
    llm_provider="openai",
    agent_task=AGENT_TASK,
)
WORKFLOW = AgentWorkflow(llm=LLM, mcp_client=None, timeout=600)


def _event_to_log(event: Event) -> str | None:
    if isinstance(event, ThinkingEvent):
        return f"**Thought**: {event.content}"
    elif isinstance(event, PromptEvent):
        return f"**Observation**: {event.content}"
    elif isinstance(event, ToolCallEvent):
        return f"Calling tool **{event.tool_name}** with input:\n\n```json\n{json.dumps(event.tool_input, indent=2)}\n```"
    elif isinstance(event, ToolResultEvent):
        return f"Result for tool **{event.tool_name}**: {event.result}"
    elif isinstance(event, OutputEvent):
        if event.final_output is not None:
            return f"**Final response**: {event.final_output}"
        return f"**Error**: {event.error}"
    return None


async def handle_prompt(text: str) -> str:
    input_event = InputEvent(prompt=text, mode="bypass")
    handler = WORKFLOW.run(start_event=input_event)
    report = ""
    async for event in handler.stream_events():
        log = _event_to_log(event)
        if log is not None:
            report += log + "\n"
    result = await handler
    log = _event_to_log(result)
    if log is not None:
        report += log + "\n"
    return report


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
