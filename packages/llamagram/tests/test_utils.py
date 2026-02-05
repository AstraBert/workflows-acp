import os
from pathlib import Path
from typing import cast
from unittest.mock import Mock, patch

import pytest
from telegram import Document, User
from telegram.ext import CallbackContext
from workflows_acp.llm_wrapper import LLMWrapper
from workflows_acp.llms.openai_llm import OpenAILLM
from workflows_acp.tools.agentfs import load_all_files
from workflows_acp.workflow import AgentWorkflow

from llamagram.constants import (
    DATA_DIR,
    DEFAULT_TO_AVOID,
    DEFAULT_TO_AVOID_FILES,
    SPECIAL_CHARS,
)
from llamagram.tools.llamacloud import _read_file_from_agentfs
from llamagram.utils import (
    _escape_markdow_for_tg,
    _event_to_log,
    _remove_temporary_report_file,
    _setup_agentfs,
    _write_temporary_report_file,
    get_llm,
    get_workflow,
    handle_documents,
    handle_prompt,
    start,
)

from .conftest import (
    AgentWorkflowMock,
    TelegramCallBackContextMock,
    TelegramDocumentMock,
    TelegramUserMock,
    WorkflowHandlerMock,
)


def test_start() -> None:
    user = cast(User, TelegramUserMock(username="hello"))
    message = start(user)
    assert (
        message
        == """
Hello there, @hello!
I am LlamaGram, your personal assistant for whatever concerns documents.
I can navigate the filesystem from the directory where you deployed me, and perform operations based on your text messages.
You can also upload PDF documents from this chat, that I will download and will be able to use afterwards.
With this being said, please, ask any questions you like!
    """
    )
    user = cast(User, TelegramUserMock(username=None))
    message = start(user)
    assert (
        message
        == """
Hello there, Llama Enthusiast!
I am LlamaGram, your personal assistant for whatever concerns documents.
I can navigate the filesystem from the directory where you deployed me, and perform operations based on your text messages.
You can also upload PDF documents from this chat, that I will download and will be able to use afterwards.
With this being said, please, ask any questions you like!
    """
    )
    message1 = start(None)
    assert message == message1


@pytest.mark.asyncio
async def test_handle_documents_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("Hello world")
    await load_all_files(
        to_avoid_dirs=DEFAULT_TO_AVOID,
        to_avoid_files=DEFAULT_TO_AVOID_FILES,
    )
    document = cast(
        Document, TelegramDocumentMock(file_name="hello.pdf", file_id="123")
    )
    callback_context = cast(CallbackContext, TelegramCallBackContextMock())
    result = await handle_documents(document, callback_context)
    path = os.path.join(DATA_DIR, "hello.pdf")
    assert (
        result
        == f"Your file has been successfully downloaded at: {path}. Use this path to reference the file in your follow-up requests to the agent"
    )


@pytest.mark.asyncio
async def test_handle_documents_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("Hello world")
    await load_all_files(
        to_avoid_dirs=DEFAULT_TO_AVOID,
        to_avoid_files=DEFAULT_TO_AVOID_FILES,
    )
    document = cast(
        Document, TelegramDocumentMock(file_name="hello.pdf", file_id="123")
    )
    callback_context = cast(
        CallbackContext, TelegramCallBackContextMock(should_fail=True)
    )
    result = await handle_documents(document, callback_context)
    assert (
        result
        == "There was an error while downloading your file, please try re-uploading"
    )


@pytest.mark.asyncio
async def test_get_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    get_llm.cache_clear()
    monkeypatch.setenv("LLAMAGRAM_LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLAMAGRAM_LLM_MODEL", "gpt-5")
    monkeypatch.setenv("LLAMAGRAM_LLM_API_KEY", "secret-key")
    llm = get_llm()
    assert llm.model == "gpt-5"
    assert isinstance(llm._client, OpenAILLM)
    assert llm._client.api_key == "secret-key"


@pytest.mark.asyncio
async def test_get_llm_nondefault_key(monkeypatch: pytest.MonkeyPatch) -> None:
    get_llm.cache_clear()
    monkeypatch.setenv("LLAMAGRAM_LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLAMAGRAM_LLM_MODEL", "gpt-5")
    monkeypatch.setenv("OPENAI_API_KEY", "secret-key")
    llm = get_llm()
    assert llm.model == "gpt-5"
    assert isinstance(llm._client, OpenAILLM)
    assert llm._client.api_key == "secret-key"


@pytest.mark.asyncio
async def test_get_llm_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    get_llm.cache_clear()
    monkeypatch.setenv("LLAMAGRAM_LLM_API_KEY", "secret-key")
    llm = get_llm()
    assert llm.model == "gpt-4.1"
    assert isinstance(llm._client, OpenAILLM)
    assert llm._client.api_key == "secret-key"


@pytest.mark.asyncio
async def test_get_llm_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    get_llm.cache_clear()
    monkeypatch.setenv("LLAMAGRAM_LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLAMAGRAM_LLM_MODEL", "gpt-5")
    monkeypatch.setenv("GOOGLE_API_KEY", "secret-key")
    with pytest.raises(
        ValueError,
        match="OPENAI_API_KEY not found within the current environment: please export it or provide it to the class constructor.",
    ):
        get_llm()
    get_llm.cache_clear()
    monkeypatch.setenv("LLAMAGRAM_LLM_PROVIDER", "opena")
    with pytest.raises(
        ValueError,
        match="Unsupported model provider: opena",
    ):
        get_llm()
    get_llm.cache_clear()
    monkeypatch.setenv("LLAMAGRAM_LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLAMAGRAM_LLM_MODEL", "gpt-6")
    with pytest.raises(
        ValueError,
        match="Unsupported model for provider openai: gpt-6",
    ):
        get_llm()


def test_get_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLAMAGRAM_LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLAMAGRAM_LLM_MODEL", "gpt-5")
    monkeypatch.setenv("LLAMAGRAM_LLM_API_KEY", "secret-key")
    get_llm.cache_clear()
    get_workflow.cache_clear()
    workflow = get_workflow()
    assert get_llm.cache_info().currsize == 1
    assert isinstance(workflow, AgentWorkflow)
    assert workflow._timeout == 600
    assert isinstance(workflow.llm, LLMWrapper)
    get_workflow.cache_clear()


@pytest.mark.asyncio
async def test_handle_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with patch("llamagram.utils.get_workflow", new_callable=Mock) as mock_get_workflow:
        mock_get_workflow.return_value = AgentWorkflowMock()
        report, final_answer = await handle_prompt("Hello")
        # check that the mock workflow actually ran
        with open(tmp_path / "app.log", "r") as f:
            content = f.readlines()
        actual_events = [
            "ThinkingEvent",
            "ToolCallEvent",
            "ToolResultEvent",
            "PromptEvent",
            "OutputEvent",
        ]
        for i, line in enumerate(content):
            assert actual_events[i] == line.strip()
        report_check = ""
        handler = WorkflowHandlerMock()
        for event in handler._events:
            log = _event_to_log(event)
            if log is not None:
                report_check += log + "\n"
        final_answer_check = _event_to_log(handler._output_event)
        assert final_answer_check is not None
        report_check += final_answer_check + "\n"
        assert final_answer == final_answer_check
        assert report == report_check


def test_escape_markdown() -> None:
    text = """The quick\\brown fox_jumped *over* the [lazy] dog (who was ~sleeping~ under a `tree`).
    > "Wait!" said the fox, < 50% certain.
    The dog & cat were #1 friends + allies - they had = rights | shared {toys}.
    Dr. Smith! Was that you?"""
    escaped_text = text
    for char in SPECIAL_CHARS:
        escaped_text = escaped_text.replace(char, f"\\{char}")
    assert _escape_markdow_for_tg(text) == escaped_text


@pytest.mark.asyncio
async def test_write_and_remove_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = await _write_temporary_report_file("hello world")
    assert (tmp_path / path).is_file()
    assert (tmp_path / path).read_text() == "hello world"
    await _remove_temporary_report_file(path)
    assert not (tmp_path / path).is_file()


@pytest.mark.asyncio
async def test_setup_agentfs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("hello")
    (tmp_path / ".env.production").write_text("greetings")
    (tmp_path / ".pypirc").write_text("bye")
    await _setup_agentfs()
    content = await _read_file_from_agentfs("test.txt")
    assert content.decode("utf-8") == "hello"
    with pytest.raises(FileNotFoundError):
        await _read_file_from_agentfs(".env.production")
    with pytest.raises(FileNotFoundError):
        await _read_file_from_agentfs(".pypirc")
