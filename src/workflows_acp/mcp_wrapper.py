import json

from typing import Any, Union
from rich import print as rprint
from dataclasses import dataclass, field, asdict
from mcp_use.client.session import (
    MCPSession,
    Tool as McpTool,
)
from mcp_use.client import MCPClient
from .models import Tool


@dataclass
class StdioMcpServer:
    command: str
    args: list[str] | None = field(default=None)
    env: dict[str, Any] | None = field(default=None)


@dataclass
class HttpMcpServer:
    url: str
    headers: dict[str, Any] | None = field(default=None)


class McpValidationError(Exception):
    """Raise when we cannot determine whether an MCP uses HTTP/SSE or stdio transport"""


McpServer = Union[StdioMcpServer, HttpMcpServer]


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
    def __init__(self, mcp_servers: dict[str, Any]) -> None:
        self.mcp_servers: dict[str, dict] = {}
        for server in mcp_servers:
            try:
                self.mcp_servers[server] = asdict(
                    _validate_mcp_server(mcp_servers[server])
                )
            except McpValidationError:
                rprint(
                    f"[yellow bold]WARNING[/]\tSkipping {server} because we cannot validate it as either a stdio or a HTTP/SSE server"
                )
        if len(self.mcp_servers) == 0:
            raise ValueError("You should provide a valid set of MCP servers")
        self._client = MCPClient.from_dict(config=self.mcp_servers)

    @classmethod
    def from_file(cls, config_file: str = ".mcp.json") -> "McpWrapper":
        with open(config_file, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict), (
            f"MCP servers configuration in {config_file} is not a valid JSON map"
        )
        assert len(data) > 0, f"MCP servers configuration in {config_file} is empty"
        return cls(mcp_servers=data)

    async def all_tools(self) -> list[Tool]:
        available_tools: list[Tool] = []
        for server in self.mcp_servers:
            session: MCPSession = await self._client.create_session(server_name=server)
            if not session.is_connected:
                await session.connect()
            tools: list[McpTool] = await session.list_tools()
            for tool in tools:
                available_tools.append(Tool.from_mcp_tool(tool, server))
        return available_tools
