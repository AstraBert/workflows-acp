import json
import re

from typing import Any, Union, TypedDict, cast
from rich import print as rprint
from mcp_use.client.session import (
    MCPSession,
    Tool as McpTool,
)
from mcp_use.client import MCPClient
from .models import Tool
from .constants import MCP_CONFIG_FILE


class StdioMcpServer(TypedDict):
    command: str
    args: list[str] | None
    env: dict[str, Any] | None


class HttpMcpServer(TypedDict):
    url: str
    headers: dict[str, Any] | None

McpServer = Union[StdioMcpServer, HttpMcpServer]

class McpServersConfig(TypedDict):
    mcpServers: dict[str, McpServer]

class McpValidationError(Exception):
    """Raise when we cannot determine whether an MCP uses HTTP/SSE or stdio transport"""

def _validate_mcp_server(mcp_server: dict[str, Any]) -> StdioMcpServer | HttpMcpServer:
    if "command" in mcp_server:
        return StdioMcpServer(
            command=mcp_server["command"],
            args=mcp_server.get("args"),
            env=mcp_server.get("env"),
        )
    elif "url" in mcp_server:
        return HttpMcpServer(url=mcp_server["url"], headers=mcp_server.get("headers"))
    else:
        raise McpValidationError(
            "Couldn't find neither 'command' nor 'url' in the current MCP server definition"
        )


class McpWrapper:
    def __init__(self, mcp_servers: dict[str, Any], from_config_dict: bool = False) -> None:
        if not from_config_dict:
            self.mcp_servers: McpServersConfig = {"mcpServers": {}}
            for server in mcp_servers["mcpServers"]:
                try:
                    self.mcp_servers["mcpServers"][server] = _validate_mcp_server(mcp_servers["mcpServers"][server])
                except McpValidationError:
                    rprint(
                        f"[yellow bold]WARNING[/]\tSkipping {server} because we cannot validate it as either a stdio or a HTTP/SSE server"
                    )
        else:
            self.mcp_servers = cast(McpServersConfig, mcp_servers)
        if len(self.mcp_servers) == 0:
            raise ValueError("You should provide a valid set of MCP servers")
        self._client = MCPClient.from_dict(config=cast(dict[str, Any], self.mcp_servers))

    @classmethod
    def from_file(cls) -> "McpWrapper":
        assert MCP_CONFIG_FILE.exists() and MCP_CONFIG_FILE.is_file(), f"No such file: {str(MCP_CONFIG_FILE)}"
        with open(MCP_CONFIG_FILE, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict), (
            f"MCP servers configuration in {str(MCP_CONFIG_FILE)} is not a valid JSON map"
        )
        assert "mcpServers" in data, f"MCP servers configuration in {str(MCP_CONFIG_FILE)} does not contain mandatory "
        assert len(data["mcpServers"]) > 0, f"MCP servers configuration in {str(MCP_CONFIG_FILE)} is empty"
        return cls(mcp_servers=data)
    
    @classmethod
    def from_config_dict(cls, servers_config: McpServersConfig) -> "McpWrapper":
        return cls(mcp_servers=cast(dict[str, Any], servers_config), from_config_dict=True)

    async def all_tools(self) -> list[Tool]:
        available_tools: list[Tool] = []
        for server in self.mcp_servers["mcpServers"]:
            session: MCPSession = await self._client.create_session(server_name=server)
            if not session.is_connected:
                await session.connect()
            tools: list[McpTool] = await session.list_tools()
            for tool in tools:
                available_tools.append(Tool.from_mcp_tool(tool, server))
        return available_tools
    
    async def call_tool(self, tool_name: str, tool_input: dict[str, Any], server: str) -> Any:
        assert tool_name.startswith("mcp_"), f"Cannot call a non-MCP tool with an MCP client. If {tool_name} this is meant to be an MCP tool, please rename it so that it starts with `mcp_`"
        _impl_tool_name = re.sub(r"^mcp_", "", tool_name, 1)
        session: MCPSession = await self._client.create_session(server_name=server)
        if not session.is_connected:
            await session.connect()
        try:
            result = await session.call_tool(name=_impl_tool_name, arguments=tool_input)
        except Exception as e:
            result = f"An error occurred while calling MCP tool {tool_name} from server {server} with arguments {tool_input}: {e}"
        return result
