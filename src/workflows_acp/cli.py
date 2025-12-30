import asyncio
import os
import yaml

from rich import print as rprint
from pathlib import Path
from typer import Typer, Option, Exit
from typing import Annotated, Literal
from .tools import DefaultToolType

app = Typer(name="wfacp", help="Run a LlamaIndex Agent Workflow with ACP communication")


@app.command(
    name="run",
    help="Run the ACP agent over stdio communication. Best if done with toad: `toad acp wfacp run`",
)
def main(
    config_file: Annotated[
        str,
        Option(
            "--config",
            "-c",
            help="Agent configuration file. For an example, see: https://github.com/AstraBert/workflows-acp/blob/main/agent_config.yaml",
        ),
    ] = "agent_config.yaml",
) -> None:
    from .acp_wrapper import start_agent

    if Path(config_file).exists() and Path(config_file).is_file():
        if os.getenv("GOOGLE_API_KEY") is None:
            rprint("[bold red]ERROR[/]\tGOOGLE_API_KEY not set in the environment")
            raise Exit(1)
        asyncio.run(start_agent(config_file=config_file))
    else:
        rprint(f"[bold red]ERROR[/]\tNo such file: {config_file}")
        raise Exit(2)


@app.command(
    name="model", help="Add/modify the LLM model in the agent configuration file"
)
def set_model(
    model: Annotated[str, Option("--model", "-m", help="Gemini model to use")],
    config_file: Annotated[
        str,
        Option(
            "--config",
            "-c",
            help="Agent configuration file. For an example, see: https://github.com/AstraBert/workflows-acp/blob/main/agent_config.yaml",
        ),
    ] = "agent_config.yaml",
) -> None:
    if Path(config_file).exists() and Path(config_file).is_file():
        with open(config_file, "r") as f:
            data = yaml.safe_load(f)
        data["model"] = model
        with open(config_file, "w") as f:
            yaml.safe_dump(data, f)
    else:
        rprint(f"[bold red]ERROR[/]\tNo such file: {config_file}")
        raise Exit(2)


@app.command(name="add-tool", help="Add a tool to the agent configuration file")
def add_tool(
    tool: Annotated[
        DefaultToolType, Option("--tool", "-t", help="Tool to add", show_choices=True)
    ],
    config_file: Annotated[
        str,
        Option(
            "--config",
            "-c",
            help="Agent configuration file. For an example, see: https://github.com/AstraBert/workflows-acp/blob/main/agent_config.yaml",
        ),
    ] = "agent_config.yaml",
) -> None:
    if Path(config_file).exists() and Path(config_file).is_file():
        with open(config_file, "r") as f:
            data = yaml.safe_load(f)
        if "tools" in data:
            assert isinstance(data["tools"], list)
            if tool not in data["tools"]:
                data["tools"].append(tool)
        else:
            data["tools"] = [tool]
        with open(config_file, "w") as f:
            yaml.safe_dump(data, f)
    else:
        rprint(f"[bold red]ERROR[/]\tNo such file: {config_file}")
        raise Exit(2)


@app.command(name="rm-tool", help="Remove a tool from the agent configuration file")
def rm_tool(
    tool: Annotated[
        DefaultToolType,
        Option("--tool", "-t", help="Tool to remove", show_choices=True),
    ],
    config_file: Annotated[
        str,
        Option(
            "--config",
            "-c",
            help="Agent configuration file. For an example, see: https://github.com/AstraBert/workflows-acp/blob/main/agent_config.yaml",
        ),
    ] = "agent_config.yaml",
) -> None:
    if Path(config_file).exists() and Path(config_file).is_file():
        with open(config_file, "r") as f:
            data = yaml.safe_load(f)
        if "tools" in data:
            assert isinstance(data["tools"], list)
            if tool in data["tools"]:
                data["tools"] = [t for t in data["tools"] if t != tool]
        with open(config_file, "w") as f:
            yaml.safe_dump(data, f)
    else:
        rprint(f"[bold red]ERROR[/]\tNo such file: {config_file}")
        raise Exit(2)


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
    config_file: Annotated[
        str,
        Option(
            "--config",
            "-c",
            help="Agent configuration file. For an example, see: https://github.com/AstraBert/workflows-acp/blob/main/agent_config.yaml",
        ),
    ] = "agent_config.yaml",
) -> None:
    if Path(config_file).exists() and Path(config_file).is_file():
        with open(config_file, "r") as f:
            data = yaml.safe_load(f)
        data["mode"] = mode
        with open(config_file, "w") as f:
            yaml.safe_dump(data, f)
    else:
        rprint(f"[bold red]ERROR[/]\tNo such file: {config_file}")
        raise Exit(2)


@app.command(name="task", help="Set the agent task within the configuration file")
def set_task(
    task: Annotated[
        str, Option("--task", "-t", help="Task (special instructions) for the agent.")
    ],
    config_file: Annotated[
        str,
        Option(
            "--config",
            "-c",
            help="Agent configuration file. For an example, see: https://github.com/AstraBert/workflows-acp/blob/main/agent_config.yaml",
        ),
    ] = "agent_config.yaml",
) -> None:
    if Path(config_file).exists() and Path(config_file).is_file():
        with open(config_file, "r") as f:
            data = yaml.safe_load(f)
        data["agent_task"] = task
        with open(config_file, "w") as f:
            yaml.safe_dump(data, f)
    else:
        rprint(f"[bold red]ERROR[/]\tNo such file: {config_file}")
        raise Exit(2)
