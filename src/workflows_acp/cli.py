import asyncio
import json
import yaml

from rich import print as rprint
from typer import Typer, Option, Exit
from typing import Annotated, Literal, Any
from .models import AvailableModel
from .tools import DefaultToolType
from .tools.agentfs import load_all_files
from .constants import AGENT_CONFIG_FILE, MCP_CONFIG_FILE
from .mcp_wrapper import (
    HttpMcpServer,
    StdioMcpServer,
    McpServersConfig,
    _validate_mcp_server,
)

app = Typer(name="wfacp", help="Run a LlamaIndex Agent Workflow with ACP communication")


@app.command(
    name="run",
    help="Run the ACP agent over stdio communication. Best if done with toad: `toad acp wfacp run`",
)
def main(
    use_mcp: Annotated[
        bool,
        Option(
            "--mcp/--no-mcp",
            help="Add MCP servers configured within the `.mcp.json` file. Defaults to true",
            is_flag=True,
        ),
    ] = True,
    use_agentfs: Annotated[
        bool,
        Option(
            "--agentfs/--no-agentfs",
            help="Use AgentFS virtual filesystem instead of your real one.",
            is_flag=True,
        ),
    ] = False,
    agentfs_skip_file: Annotated[
        list[str],
        Option(
            "--agentfs-skip-file",
            help="Exclude one or more files from being uploaded to AgentFS. Can be used multiple times. Only considered if `--agentfs` is passed.",
        ),
    ] = [],
    agentfs_skip_dir: Annotated[
        list[str],
        Option(
            "--agentfs-skip-dir",
            help="Exclude one or more directories from being uploaded to AgentFS. Can be used multiple times. Only considered if `--agentfs` is passed.",
        ),
    ] = [],
) -> None:
    from .acp_wrapper import start_agent

    asyncio.run(
        start_agent(
            from_config_file=True,
            use_mcp=use_mcp,
            use_agentfs=use_agentfs,
            agentfs_skip_dirs=agentfs_skip_dir if len(agentfs_skip_dir) > 0 else None,
            agentfs_skip_files=agentfs_skip_file
            if len(agentfs_skip_file) > 0
            else None,
        )
    )


@app.command(
    name="load-agentfs",
    help="Load all the files in the current directory to AgentFS before running the agent.",
)
def load_agentfs(
    skip_file: Annotated[
        list[str],
        Option(
            "--skip-file",
            help="Exclude one or more files from being uploaded to AgentFS. Can be used multiple times.",
        ),
    ] = [],
    skip_dir: Annotated[
        list[str],
        Option(
            "--skip-dir",
            help="Exclude one or more directories from being uploaded to AgentFS. Can be used multiple times.",
        ),
    ] = [],
) -> None:
    asyncio.run(
        load_all_files(
            to_avoid_dirs=skip_dir if len(skip_dir) > 0 else None,
            to_avoid_files=skip_file if len(skip_file) > 0 else None,
            progress=True,
        )
    )


@app.command(
    name="model", help="Add/modify the LLM model in the agent configuration file"
)
def set_model(
    model: Annotated[
        AvailableModel,
        Option("--model", "-m", help="LLM model to use", show_choices=True),
    ],
) -> None:
    _from_scratch = False
    if not AGENT_CONFIG_FILE.exists():
        _from_scratch = True
        AGENT_CONFIG_FILE.touch()
    if not _from_scratch:
        with open(AGENT_CONFIG_FILE, "r") as f:
            data = yaml.safe_load(f)
    else:
        data = {}
    data["model"] = model
    with open(AGENT_CONFIG_FILE, "w") as f:
        yaml.safe_dump(data, f)


@app.command(name="add-tool", help="Add a tool to the agent configuration file")
def add_tool(
    tool: Annotated[
        DefaultToolType, Option("--tool", "-t", help="Tool to add", show_choices=True)
    ],
) -> None:
    _from_scratch = False
    if not AGENT_CONFIG_FILE.exists():
        _from_scratch = True
        AGENT_CONFIG_FILE.touch()
    if not _from_scratch:
        with open(AGENT_CONFIG_FILE, "r") as f:
            data = yaml.safe_load(f)
    else:
        data = {}
    if "tools" in data:
        assert isinstance(data["tools"], list)
        if tool not in data["tools"]:
            data["tools"].append(tool)
    else:
        data["tools"] = [tool]
    with open(AGENT_CONFIG_FILE, "w") as f:
        yaml.safe_dump(data, f)


@app.command(name="rm-tool", help="Remove a tool from the agent configuration file")
def rm_tool(
    tool: Annotated[
        DefaultToolType,
        Option("--tool", "-t", help="Tool to remove", show_choices=True),
    ],
) -> None:
    _from_scratch = False
    if not AGENT_CONFIG_FILE.exists():
        _from_scratch = True
        AGENT_CONFIG_FILE.touch()
    if not _from_scratch:
        with open(AGENT_CONFIG_FILE, "r") as f:
            data = yaml.safe_load(f)
            if "tools" in data:
                assert isinstance(data["tools"], list)
                if tool in data["tools"]:
                    data["tools"] = [t for t in data["tools"] if t != tool]
    else:
        data = {}
    with open(AGENT_CONFIG_FILE, "w") as f:
        yaml.safe_dump(data, f)


@app.command(name="mode", help="Set a mode for the agent within the configuration file")
def set_mode(
    mode: Annotated[
        Literal["ask", "bypass"],
        Option(
            "--mode",
            "-m",
            help="Mode to set. 'ask' means that the agent asks for permission prior to tool calls, whereas 'bypass' measn that the agent bypasses permission and executes tools directly.",
            show_choices=True,
        ),
    ],
) -> None:
    _from_scratch = False
    if not AGENT_CONFIG_FILE.exists():
        _from_scratch = True
        AGENT_CONFIG_FILE.touch()
    if not _from_scratch:
        with open(AGENT_CONFIG_FILE, "r") as f:
            data = yaml.safe_load(f)
    else:
        data = {}
    data["mode"] = mode
    with open(AGENT_CONFIG_FILE, "w") as f:
        yaml.safe_dump(data, f)


@app.command(name="task", help="Set the agent task within the configuration file")
def set_task(
    task: Annotated[
        str, Option("--task", "-t", help="Task (special instructions) for the agent.")
    ],
) -> None:
    _from_scratch = False
    if not AGENT_CONFIG_FILE.exists():
        _from_scratch = True
        AGENT_CONFIG_FILE.touch()
    if not _from_scratch:
        with open(AGENT_CONFIG_FILE, "r") as f:
            data = yaml.safe_load(f)
    else:
        data = {}
    data["agent_task"] = task
    with open(AGENT_CONFIG_FILE, "w") as f:
        yaml.safe_dump(data, f)


@app.command(
    name="add-mcp", help="Add an MCP server to the `.mcp.json` configuration file"
)
def add_mcp(
    name: Annotated[str, Option("--name", "-n", help="Name of the MCP server")],
    transport: Annotated[
        Literal["stdio", "http"],
        Option(
            "--transport",
            "-t",
            help="Type of transport for the MCP server",
            show_choices=True,
        ),
    ],
    command: Annotated[
        str | None,
        Option(
            "--command",
            "-c",
            help="Command to start the stdio MCP server. Pass the entire command (including the arguments), for instance: 'npx @my-mcp/server arg1'. Will be ignored if transport is set to `http`",
        ),
    ] = None,
    env: Annotated[
        list[str],
        Option(
            "--env",
            "-e",
            help="The environment variables that should be associated to the stdio MCP server process. You can use this option multiple times, and should pass the env variable in this form: 'NAME=VALUE'. Will be ignored if transport is set to `http`",
        ),
    ] = [],
    url: Annotated[
        str | None,
        Option(
            "--url",
            "-u",
            help="URL of the HTTP MCP server. Will be ignored if transport is set to `stdio`",
        ),
    ] = None,
    headers: Annotated[
        list[str],
        Option(
            "--header",
            "-x",
            help="Header name and value to associate to requests made to an HTTP MCP server. You can use this option multiple times, and should pass the header in this form: 'NAME=VALUE'. Will be ignored if transport is set to `stdio`",
        ),
    ] = [],
) -> None:
    _from_scratch = False
    if not MCP_CONFIG_FILE.exists():
        _from_scratch = True
        MCP_CONFIG_FILE.touch()
    if not _from_scratch:
        with open(MCP_CONFIG_FILE, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict), (
            f"File {str(MCP_CONFIG_FILE)} does not contain a valid JSON map"
        )
        assert "mcpServers" in data, (
            f"File {str(MCP_CONFIG_FILE)} does not contain the 'mcpServers' key needed for a valid MCP configuration"
        )
        mcp_servers_config: McpServersConfig = {"mcpServers": {}}
        for server in data["mcpServers"]:
            mcp_servers_config["mcpServers"][server] = _validate_mcp_server(
                data["mcpServers"][server]
            )
    else:
        mcp_servers_config: McpServersConfig = {"mcpServers": {}}
    if transport == "stdio":
        cmd = None
        args: list[str] | None = None
        cmd_env: dict[str, Any] = {}
        if command is not None:
            mcp_cmd = command.split(" ")
            cmd = mcp_cmd[0]
            if len(mcp_cmd) > 1:
                args = mcp_cmd[1:]
        else:
            rprint(
                "[bold red]ERROR:[/]\tIf transport is set to stdio, you should provide a command."
            )
            raise Exit(1)
        if len(env) > 0:
            for s in env:
                assert "=" in s and len(s.split("=")) == 2, (
                    f"env variables should be provided as 'NAME=VALUE', but {s} is not"
                )
                cmd_env[s.split("=")[0]] = s.split("=")[1]
        mcp_servers_config["mcpServers"][name] = StdioMcpServer(
            command=cmd, args=args, env=cmd_env
        )
    else:
        mcp_url = None
        mcp_headers: dict[str, Any] = {}
        if url is None:
            rprint(
                "[bold red]ERROR:[/]\tIf transport is set to http, you should provide a URL."
            )
            raise Exit(2)
        else:
            mcp_url = url
        if len(headers) > 0:
            for s in headers:
                assert "=" in s and len(s.split("=")) == 2, (
                    f"headers should be provided as 'NAME=VALUE', but {s} is not"
                )
                mcp_headers[s.split("=")[0]] = s.split("=")[1]
        mcp_servers_config["mcpServers"][name] = HttpMcpServer(
            url=mcp_url,
            headers=mcp_headers,
        )
    with open(MCP_CONFIG_FILE, "w") as f:
        json.dump(mcp_servers_config, f, indent=2)


@app.command(
    name="rm-mcp", help="Remove an MCP server from the `.mcp.json` configuration file"
)
def remove_mcp(
    name: Annotated[
        str, Option("--name", "-n", help="Name of the MCP server to remove")
    ],
) -> None:
    _from_scratch = False
    if not MCP_CONFIG_FILE.exists():
        _from_scratch = True
        MCP_CONFIG_FILE.touch()
    if not _from_scratch:
        with open(MCP_CONFIG_FILE, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict), (
            f"File {str(MCP_CONFIG_FILE)} does not contain a valid JSON map"
        )
        assert "mcpServers" in data, (
            f"File {str(MCP_CONFIG_FILE)} does not contain the 'mcpServers' key needed for a valid MCP configuration"
        )
        mcp_servers_config: McpServersConfig = {"mcpServers": {}}
        for server in data["mcpServers"]:
            mcp_servers_config["mcpServers"][server] = _validate_mcp_server(
                data["mcpServers"][server]
            )
    else:
        mcp_servers_config: McpServersConfig = {"mcpServers": {}}
    if name in mcp_servers_config["mcpServers"]:
        mcp_servers_config["mcpServers"].pop(name)
    with open(MCP_CONFIG_FILE, "w") as f:
        json.dump(mcp_servers_config, f, indent=2)
