import pytest
import json

from unittest.mock import patch
from typing import cast, Any
from pathlib import Path
from copy import deepcopy
from workflows_acp.models import Tool
from workflows_acp.mcp_wrapper import (
    McpWrapper,
    _validate_mcp_server,
    HttpMcpServer,
    StdioMcpServer,
    McpServersConfig,
    McpValidationError,
    MCP_CONFIG_FILE,
)
from .conftest import MockMcpClient, MCP_TOOLS

MCP_CONFIG = McpServersConfig(
    mcpServers={
        "with-stdio": StdioMcpServer(command="npx", args=["@mcp/server"], env=None),
        "with-http": HttpMcpServer(
            url="https://example.com/mcp",
            headers=None,
        ),
    }
)


def setup_folder(tmp_path: Path) -> None:
    mcp_file = tmp_path / ".mcp.json"
    with open(mcp_file, "w") as f:
        json.dump(MCP_CONFIG, f, indent=2)


def test__validate_mcp_servers() -> None:
    for server_name in MCP_CONFIG["mcpServers"]:
        server = MCP_CONFIG["mcpServers"][server_name]
        assert isinstance(_validate_mcp_server(cast(dict[str, Any], server)), dict)
    mcp_config_copy = deepcopy(MCP_CONFIG)
    for server_name in mcp_config_copy["mcpServers"]:
        server = mcp_config_copy["mcpServers"][server_name]
        if "command" in server:
            server.pop("command")
        else:
            server.pop("url")
        with pytest.raises(McpValidationError):
            _validate_mcp_server(cast(dict[str, Any], server))


def test_mcp_wrapper_init(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path)
    monkeypatch.chdir(tmp_path)
    with patch("workflows_acp.mcp_wrapper.MCPClient", new=MockMcpClient) as cls:
        mcp_client = McpWrapper.from_config_dict(MCP_CONFIG)
        assert mcp_client.mcp_servers == MCP_CONFIG
        assert isinstance(mcp_client._client, cls)
        assert MCP_CONFIG_FILE.exists()
        mcp_client_1 = McpWrapper.from_file()
        assert mcp_client_1.mcp_servers == MCP_CONFIG
        assert isinstance(mcp_client_1._client, cls)


@pytest.mark.asyncio
async def test_mcp_wrapper_methods(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path)
    monkeypatch.chdir(tmp_path)
    with patch("workflows_acp.mcp_wrapper.MCPClient", new=MockMcpClient) as _:
        mcp_client = McpWrapper.from_config_dict(MCP_CONFIG)
        tools = await mcp_client.all_tools()
        actual_tool = Tool.from_mcp_tool(MCP_TOOLS[0], "with-stdio")
        assert len(tools) == 2
        assert tools[0].name == actual_tool.name
        assert tools[0].description == actual_tool.description
        assert tools[0].fn is None
        assert tools[0].mcp_metadata == actual_tool.mcp_metadata
        result = await mcp_client.call_tool(
            tool_name="mcp_add", tool_input={"x": 1, "y": 1}, server="with-stdio"
        )
        assert result == "Called tool add with arguments: {'x': 1, 'y': 1}"
