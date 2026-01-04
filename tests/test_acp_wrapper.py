import pytest
import json
import os
import logging

from pathlib import Path
from typing import cast
from unittest.mock import patch
from acp import PROTOCOL_VERSION
from acp.schema import (
    AuthenticateResponse,
    InitializeResponse,
    LoadSessionResponse,
    NewSessionResponse,
    PromptResponse,
    SetSessionModeResponse,
    ListSessionsResponse,
    AgentCapabilities,
    Implementation,
    PromptCapabilities,
    McpCapabilities,
    SessionModeState,
    TextContentBlock,
)
from acp.interfaces import Client
from workflows_acp.acp_wrapper import _create_agent
from workflows_acp.constants import DEFAULT_MODEL, VERSION, MODES
from workflows_acp.tools import TOOLS, filter_tools
from .conftest import (
    MockWorkflow,
    MockLLMWrapper,
    MockMcpWrapper,
    MockACPClient,
    MCP_CONFIG_ONE,
)


def setup_folder(tmp_path: Path, with_agentfs: bool = False) -> None:
    with open("tests/testfiles/agent_config.yaml", "r") as f:
        content = f.read()
    mcp_file = tmp_path / ".mcp.json"
    with open(mcp_file, "w") as f:
        json.dump(MCP_CONFIG_ONE, f, indent=2)
    agent_file = tmp_path / "agent_config.yaml"
    with open(agent_file, "w") as f:
        f.write(content)
    if with_agentfs:
        agentfs_file = tmp_path / "agent.db"
        agentfs_file.touch()


@pytest.mark.asyncio
async def test_acp_wrapper_init(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-api-key")
    with patch("workflows_acp.acp_wrapper.McpWrapper", new=MockMcpWrapper) as _:
        with patch("workflows_acp.acp_wrapper.LLMWrapper", new=MockLLMWrapper) as _:
            with patch(
                "workflows_acp.acp_wrapper.AgentWorkflow", new=MockWorkflow
            ) as _:
                # from programmatic config
                agent = await _create_agent(mcp_config=MCP_CONFIG_ONE)
                for i, tool in enumerate(agent._llm.tools):
                    assert tool.name == TOOLS[i].name
                assert agent._mode == "ask"
                assert agent._llm.model == DEFAULT_MODEL
                assert agent._mcp_client is not None
                assert agent._mcp_client.mcp_servers == MCP_CONFIG_ONE
                # without MCP
                agent = await _create_agent(use_mcp=False)
                assert agent._mcp_client is None
                # from files
                agent = await _create_agent(from_config_file=True)
                assert agent._mcp_client is not None
                assert agent._mcp_client.mcp_servers == MCP_CONFIG_ONE
                tool_names = [tool.name for tool in agent._llm.tools]
                assert (
                    "write_file" in tool_names
                    and "edit_file" in tool_names
                    and "read_file" in tool_names
                    and "glob_paths" in tool_names
                )
                assert agent._llm.model == "gemini-3-pro-preview"
                assert agent._mode == "bypass"


@pytest.mark.asyncio
async def test_acp_wrapper_init_agentfs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    setup_folder(tmp_path, with_agentfs=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-api-key")
    with patch("workflows_acp.acp_wrapper.McpWrapper", new=MockMcpWrapper) as _:
        with patch("workflows_acp.acp_wrapper.LLMWrapper", new=MockLLMWrapper) as _:
            with patch(
                "workflows_acp.acp_wrapper.AgentWorkflow", new=MockWorkflow
            ) as _:
                with caplog.at_level(logging.DEBUG):
                    # from programmatic config
                    agent = await _create_agent(from_config_file=True, use_agentfs=True)
                    assert (
                        "Detected agent.db in current working directory, will not load files."
                        in caplog.text
                    )
                    tool_names = [tool.name for tool in agent._llm.tools]
                    assert (
                        "write_file" in tool_names
                        and "edit_file" in tool_names
                        and "read_file" in tool_names
                        and "glob_paths" in tool_names
                    )
                    # glob_paths has a slightly different description if use_agentfs is provided
                    assert (
                        agent._llm.tools[tool_names.index("glob_paths")].description
                        == filter_tools(names=["glob_paths"], use_agentfs=True)[
                            0
                        ].description
                    )
                    os.remove(tmp_path / "agent.db")
                    agent = await _create_agent(from_config_file=True, use_agentfs=True)
                    assert (
                        "Loading all files in the current working directory to AgentFS"
                        in caplog.text
                        and "Finished loading all files in the current working directory to AgentFS"
                        in caplog.text
                    )


@pytest.mark.asyncio
async def test_acp_wrapper_main_methods(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-api-key")
    with patch("workflows_acp.acp_wrapper.McpWrapper", new=MockMcpWrapper) as _:
        with patch("workflows_acp.acp_wrapper.LLMWrapper", new=MockLLMWrapper) as _:
            with patch(
                "workflows_acp.acp_wrapper.AgentWorkflow", new=MockWorkflow
            ) as _:
                # from programmatic config
                agent = await _create_agent(from_config_file=True)
                agent._conn = cast(Client, MockACPClient())
                resp = await agent.initialize(protocol_version=PROTOCOL_VERSION)
                assert isinstance(resp, InitializeResponse)
                assert (
                    resp.model_dump_json()
                    == InitializeResponse(
                        protocol_version=PROTOCOL_VERSION,
                        agent_capabilities=AgentCapabilities(
                            prompt_capabilities=PromptCapabilities(
                                image=False, audio=False, embedded_context=False
                            ),
                            mcp_capabilities=McpCapabilities(http=False, sse=False),
                        ),
                        agent_info=Implementation(
                            name="workflows-acp", title="AgentWorkflow", version=VERSION
                        ),
                    ).model_dump_json()
                )
                auth_resp = await agent.authenticate(method_id="hello")
                assert isinstance(auth_resp, AuthenticateResponse)
                assert (
                    auth_resp.model_dump_json()
                    == AuthenticateResponse().model_dump_json()
                )
                new_resp = await agent.new_session(cwd=".", mcp_servers=[])
                assert isinstance(new_resp, NewSessionResponse)
                assert (
                    new_resp.model_dump_json()
                    == NewSessionResponse(
                        modes=SessionModeState(
                            available_modes=MODES, current_mode_id=agent._mode
                        ),
                        session_id=str(agent._next_session_id - 1),
                    ).model_dump_json()
                )
                load_resp = await agent.load_session(
                    cwd=".", mcp_servers=[], session_id="0"
                )
                assert isinstance(load_resp, LoadSessionResponse)
                assert (
                    load_resp.model_dump_json()
                    == LoadSessionResponse(
                        modes=SessionModeState(
                            available_modes=MODES, current_mode_id=agent._mode
                        )
                    ).model_dump_json()
                )
                mode_resp = await agent.set_session_mode(
                    mode_id="bypass", session_id="0"
                )
                assert isinstance(mode_resp, SetSessionModeResponse)
                assert (
                    mode_resp.model_dump_json()
                    == SetSessionModeResponse().model_dump_json()
                )
                assert agent._mode == "bypass"
                list_resp = await agent.list_sessions()
                assert isinstance(list_resp, ListSessionsResponse)
                assert (
                    isinstance(list_resp.sessions, list)
                    and len(list_resp.sessions) == 1
                )
                assert list_resp.sessions[0].session_id == str(
                    agent._next_session_id - 1
                )
                assert (
                    list_resp.sessions[0].title
                    == f"Session {str(agent._next_session_id - 1)}"
                )
                assert list_resp.sessions[0].cwd == "."
                prompt_res = await agent.prompt(
                    prompt=[TextContentBlock(text="hello", type="text")], session_id="0"
                )
                assert (
                    prompt_res.model_dump_json()
                    == PromptResponse(stop_reason="end_turn").model_dump_json()
                )
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
                assert agent._conn.num_updates == len(content)  # type: ignore
