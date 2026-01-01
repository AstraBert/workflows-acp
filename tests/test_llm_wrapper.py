import pytest

from pathlib import Path
from unittest.mock import patch
from workflows_acp._templating import Template
from workflows_acp.constants import DEFAULT_MODEL, DEFAULT_TASK, SYSTEM_PROMPT_STRING
from workflows_acp.tools import TOOLS
from workflows_acp.llm_wrapper import LLMWrapper
from workflows_acp.models import Action, Tool
from .conftest import MockGenAIClient


def say_hello() -> str:
    return "Hello!"


HELLO_TOOL = Tool(fn=say_hello, name="say_hello", description="Say hello")


def setup_folder(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").touch()
    (tmp_path / "AGENTS.md").write_text("Hello world")


def test_llm_wrapper_init(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path)
    monkeypatch.chdir(tmp_path)
    llm = LLMWrapper(tools=[HELLO_TOOL], api_key="fake-api-key")
    assert llm.model == DEFAULT_MODEL
    assert llm.tools == [HELLO_TOOL]
    assert isinstance(llm._chat_history[0].parts, list)
    assert llm._chat_history[0].role == "system"
    assert llm._chat_history[0].parts[0].text == Template(SYSTEM_PROMPT_STRING).render(
        {
            "task": DEFAULT_TASK,
            "tools": "\n\n".join([tool.to_string() for tool in llm.tools]),
            "additional_instructions": "## Additional Instructions\n\n```md\nHello world\n```\n",
        }
    )
    with pytest.raises(
        ValueError,
        match="GOOGLE_API_KEY not found within the current environment: please export it or provide it to the class constructor.",
    ):
        LLMWrapper(tools=[HELLO_TOOL])
    with pytest.raises(
        ValueError, match="All the tools provided should have different names"
    ):
        LLMWrapper(tools=[HELLO_TOOL, HELLO_TOOL], api_key="fake-api-key")


def test_llm_wrapper_methods() -> None:
    llm = LLMWrapper(tools=TOOLS, api_key="fake-api-key")
    llm.add_user_message("hello there")
    assert len(llm._chat_history) == 2
    assert isinstance(llm._chat_history[1].parts, list)
    assert llm._chat_history[1].role == "user"
    assert llm._chat_history[1].parts[0].text == "hello there"
    tool = llm.get_tool("write_file")
    assert tool.name == "write_file"


@pytest.mark.asyncio
async def test_llm_wrapper_generate() -> None:
    with patch("workflows_acp.llm_wrapper.GenAIClient", new=MockGenAIClient) as _:
        llm = LLMWrapper(tools=[HELLO_TOOL], api_key="fake-api-key")
        result = await llm.generate(schema=Action)
        assert result is not None
        assert result.tool_call is None
        assert result.stop is not None
        assert result.stop.stop_reason == "I am done"
        assert result.stop.final_output == "this is a final result"
        assert len(llm._chat_history) == 2
        assert isinstance(llm._chat_history[1].parts, list)
        assert llm._chat_history[1].role == "assistant"
        assert llm._chat_history[1].parts[0].text == result.model_dump_json()
