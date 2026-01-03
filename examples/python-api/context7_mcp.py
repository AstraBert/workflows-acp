"""
Assistant that can use the Context7 MCP server for coding-related tasks, while also having access to filesystem, memory and TODO-tracking tools.
"""

import os
import asyncio

from workflows_acp.mcp_wrapper import McpServersConfig
from workflows_acp.acp_wrapper import start_agent
from workflows_acp.tools import DefaultToolType

MCP_CONFIG: McpServersConfig = {
    "mcpServers": {
        "context7": {
            "url": "https://mcp.context7.com/mcp",
            "headers": {"CONTEXT7_API_KEY": os.getenv("CONTEXT7_API_KEY")},
        }
    }
}

TOOLS: list[DefaultToolType] = [
    "write_file",
    "edit_file",
    "read_file",
    "write_memory",
    "read_memory",
    "create_todos",
    "update_todo",
    "list_todos",
]

AGENT_TASK = "You should provide the user with coding assistance, leveraging the documentation available to you thanks to the context7 MCP server's tools. You should also use the filesystem-based tools (write/edit/read-file) to perform file operations (only when requested by the user), memorize important information for later retrieval through the memor tools, and keep track of your tasks using the TODO tools."


async def main() -> None:
    await start_agent(
        llm_model="gemini-3-pro-preview",
        agent_task=AGENT_TASK,
        tools=TOOLS,
        mode="ask",
        mcp_config=MCP_CONFIG,
    )


if __name__ == "__main__":
    # execute with toad (or any other ACP client)
    # with toad:
    # toad acp "python3 /path/to/context7_mcp.py"
    asyncio.run(main())
