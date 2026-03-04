import asyncio
from pathlib import Path
from typing import Annotated, Literal

import uvicorn
from dotenv import set_key
from rich import print as rprint
from rich.markdown import Markdown
from rich.prompt import Prompt
from typer import Option, Typer
from workflows_acp.constants import AVAILABLE_MODELS

from .api.api import create_api_app
from .api.client import LobsterXClient
from .api.shared import LobsterXApiConfig
from .bot import run_bot
from .constants import LOG_LEVELS
from .utils import _setup_agentfs

app = Typer()


@app.command(name="run", help="Run the Telegram bot")
def run(
    log_level: Annotated[
        LOG_LEVELS,
        Option(
            "--log-level",
            "-l",
            help="Log level for the bot. Logging can easily become verbose, so a log-level of `debug` is not recommended.",
            show_choices=True,
        ),
    ] = "info",
) -> None:
    asyncio.run(run_bot(log_level=log_level))


@app.command(name="setup", help="Define LLM-related settings for the bot.")
def setup_wizard(
    llm_provider: Annotated[
        Literal["google", "openai", "anthropic"],
        Option("--provider", "-p", help="LLM provider for the bot.", show_choices=True),
    ] = "openai",
    llm_model: Annotated[
        str, Option("--model", "-m", help="LLM model for the bot")
    ] = "gpt-4.1",
    api_key: Annotated[
        str | None,
        Option(
            "--api-key",
            "-k",
            help="API key for the LLM provider. If not set, you will be prompted to provide it through standard input.",
        ),
    ] = None,
    llama_cloud_api_key: Annotated[
        str | None,
        Option(
            "--llama-cloud-key",
            "-l",
            help="API key for LlamaCloud. If not set, you will be prompted to provide it through standard input.",
        ),
    ] = None,
    telegram_token: Annotated[
        str | None,
        Option(
            "--telegram-token",
            "-t",
            help="Token for Telegram Bot. If not set, you will be prompted to provide it through standard input.",
        ),
    ] = None,
    server_key: Annotated[
        str | None,
        Option(
            "--server-key",
            "-s",
            help="API key for the server. If not set, you will be prompted to provide it through standard input.",
        ),
    ] = None,
    interactive: Annotated[
        bool,
        Option(
            "--interactive/--no-interactive",
            help="Whether or not the setup should be interactive (using prompts from standard input instead of options from CLI)",
        ),
    ] = False,
) -> None:
    if interactive:
        llm_provider = Prompt().ask(
            "LLM Provider for LobsterX",
            choices=["openai", "google", "anthropic"],
            show_choices=True,
        )  # type: ignore
        llm_model = Prompt().ask(
            "LLM Model for LobsterX",
            choices=[
                m
                for m in list(AVAILABLE_MODELS.keys())
                if AVAILABLE_MODELS[m] == llm_provider
            ],
            show_choices=True,
        )
        api_key = Prompt().ask(
            "API key for model provider",
            password=True,
        )
        llama_cloud_api_key = Prompt().ask("API key for LlamaCloud", password=True)
        telegram_token = Prompt().ask("Bot Token for Telegram", password=True)
        server_key = Prompt().ask(
            "Key for the LobsterX server (optional)", password=True
        )
    if api_key is None:
        api_key = Prompt().ask(
            "API key for model provider",
            password=True,
        )
    if llama_cloud_api_key is None:
        llama_cloud_api_key = Prompt().ask("API key for LlamaCloud", password=True)
    if telegram_token is None:
        telegram_token = Prompt().ask("Bot Token for Telegram", password=True)
    if server_key is None:
        server_key = Prompt().ask(
            "Key for the LobsterX server (optional)", password=True
        )
    dot_env = Path(".env")
    if not dot_env.exists():
        dot_env.touch()
    set_key(".env", key_to_set="LOBSTERX_LLM_PROVIDER", value_to_set=llm_provider)
    set_key(".env", key_to_set="LOBSTERX_LLM_MODEL", value_to_set=llm_model)
    set_key(".env", key_to_set="LOBSTERX_LLM_API_KEY", value_to_set=api_key)
    set_key(".env", key_to_set="LOBSTERX_SERVER_KEY", value_to_set=server_key)
    set_key(".env", key_to_set="LLAMA_CLOUD_API_KEY", value_to_set=llama_cloud_api_key)
    set_key(".env", key_to_set="TELEGRAM_BOT_TOKEN", value_to_set=telegram_token)


@app.command(name="serve", help="Run LobsterX as an API server.")
def serve(
    host: Annotated[
        str,
        Option(
            "--bind",
            "-b",
            help="Host to bind the server to. Defaults to 0.0.0.0",
        ),
    ] = "0.0.0.0",
    port: Annotated[
        int,
        Option(
            "--port",
            "-p",
            help="Port to bind the server to. Defaults to 8000",
        ),
    ] = 8000,
    allow_origins: Annotated[
        list[str],
        Option(
            "--allow",
            "-a",
            help="Origins to be allowed for CORS (can be used multiple times)",
        ),
    ] = [],
    file_downloads_per_minute: Annotated[
        int | None,
        Option(
            "--file-downloads-per-minute",
            help="Rate limit (per minute) on file downloads. Defaults to 300.",
        ),
    ] = None,
    create_tasks_per_minute: Annotated[
        int | None,
        Option(
            "--create-tasks-per-minute",
            help="Rate limit (per minute) on task creation. Defaults to 60.",
        ),
    ] = None,
    delete_tasks_per_minute: Annotated[
        int | None,
        Option(
            "--delete-tasks-per-minute",
            help="Rate limit (per minute) on task cancellation. Defaults to 60.",
        ),
    ] = None,
    poll_tasks_per_minute: Annotated[
        int | None,
        Option(
            "--poll-tasks-per-minute",
            help="Rate limit (per minute) on polling tasks for completion. Defaults to 300.",
        ),
    ] = None,
    server_api_key: Annotated[
        str | None,
        Option(
            "--server-key",
            help="API key to be used within the server to authorize requests. Reads from LOBSTERX_SERVER_KEY env variable if not provided.",
        ),
    ] = None,
    config_file: Annotated[
        str | None,
        Option(
            "--config",
            "-c",
            help="Config file from which to read the LobsterX server configuration. Configured options have precedence over CLI.",
        ),
    ] = None,
) -> None:
    if config_file is not None:
        args = LobsterXApiConfig.load_from_config(config_file)
        app = create_api_app(**args.to_args())
        port = args.port or port
        host = args.host or host
    else:
        app = create_api_app(
            allow_origins=allow_origins,
            create_tasks_per_minute=create_tasks_per_minute,
            delete_tasks_per_minute=delete_tasks_per_minute,
            poll_tasks_per_minute=poll_tasks_per_minute,
            file_downloads_per_minute=file_downloads_per_minute,
            server_api_key=server_api_key,
        )
    asyncio.run(_setup_agentfs(with_print=True))
    uvicorn.run(app, host=host, port=port)


@app.command(
    name="create-task", help="Send a request to a LobsterX server to create a task."
)
def create_task(
    prompt: str,
    protocol: Annotated[
        Literal["http", "https"],
        Option(
            "--protocol",
            "-t",
            help="Protocol for the connection. Defaults to 'http'.",
        ),
    ] = "http",
    host: Annotated[
        str,
        Option(
            "--bind",
            "-b",
            help="Host to bind the server to. Defaults to 0.0.0.0",
        ),
    ] = "0.0.0.0",
    port: Annotated[
        int,
        Option(
            "--port",
            "-p",
            help="Port to bind the server to. Defaults to 8000",
        ),
    ] = 8000,
    server_api_key: Annotated[
        str | None,
        Option(
            "--server-key",
            help="API key to be used within the server to authorize requests. Reads from LOBSTERX_SERVER_KEY env variable if not provided.",
        ),
    ] = None,
    config_file: Annotated[
        str | None,
        Option(
            "--config",
            "-c",
            help="Config file from which to read the LobsterX server configuration. Configured options have precedence over CLI.",
        ),
    ] = None,
) -> None:
    if config_file is not None:
        args = LobsterXApiConfig.load_from_config(config_file)
        port = args.port or port
        host = args.host or host
        protocol = args.protocol or protocol
    client = LobsterXClient(
        api_key=server_api_key, host=host, port=port, protocol=protocol
    )
    response = asyncio.run(client.create_task(prompt))
    print(
        f"Created task as: {response}. Please use this Task ID to poll for the result or cancel the task."
    )


@app.command(
    name="upload-file", help="Send a request to a LobsterX server to upload a file."
)
def upload_file(
    file_path: str,
    protocol: Annotated[
        Literal["http", "https"],
        Option(
            "--protocol",
            "-t",
            help="Protocol for the connection. Defaults to 'http'.",
        ),
    ] = "http",
    host: Annotated[
        str,
        Option(
            "--bind",
            "-b",
            help="Host to bind the server to. Defaults to 0.0.0.0",
        ),
    ] = "0.0.0.0",
    port: Annotated[
        int,
        Option(
            "--port",
            "-p",
            help="Port to bind the server to. Defaults to 8000",
        ),
    ] = 8000,
    server_api_key: Annotated[
        str | None,
        Option(
            "--server-key",
            help="API key to be used within the server to authorize requests. Reads from LOBSTERX_SERVER_KEY env variable if not provided.",
        ),
    ] = None,
    config_file: Annotated[
        str | None,
        Option(
            "--config",
            "-c",
            help="Config file from which to read the LobsterX server configuration. Configured options have precedence over CLI.",
        ),
    ] = None,
) -> None:
    if config_file is not None:
        args = LobsterXApiConfig.load_from_config(config_file)
        port = args.port or port
        host = args.host or host
        protocol = args.protocol or protocol
    client = LobsterXClient(
        api_key=server_api_key, host=host, port=port, protocol=protocol
    )
    response = asyncio.run(client.upload_file(file_path))
    print(
        f"Uploaded file to the server. Use the path: '{response}' to refer to the uploaded file in follow-up prompts."
    )


@app.command(
    name="get-task",
    help="Send a request to a LobsterX server to get the status of a task.",
)
def get_task(
    task_id: str,
    protocol: Annotated[
        Literal["http", "https"],
        Option(
            "--protocol",
            "-t",
            help="Protocol for the connection. Defaults to 'http'.",
        ),
    ] = "http",
    host: Annotated[
        str,
        Option(
            "--bind",
            "-b",
            help="Host to bind the server to. Defaults to 0.0.0.0",
        ),
    ] = "0.0.0.0",
    port: Annotated[
        int,
        Option(
            "--port",
            "-p",
            help="Port to bind the server to. Defaults to 8000",
        ),
    ] = 8000,
    server_api_key: Annotated[
        str | None,
        Option(
            "--server-key",
            help="API key to be used within the server to authorize requests. Reads from LOBSTERX_SERVER_KEY env variable if not provided.",
        ),
    ] = None,
    config_file: Annotated[
        str | None,
        Option(
            "--config",
            "-c",
            help="Config file from which to read the LobsterX server configuration. Configured options have precedence over CLI.",
        ),
    ] = None,
) -> None:
    if config_file is not None:
        args = LobsterXApiConfig.load_from_config(config_file)
        port = args.port or port
        host = args.host or host
        protocol = args.protocol or protocol
    client = LobsterXClient(
        api_key=server_api_key, host=host, port=port, protocol=protocol
    )
    response = asyncio.run(client.get_task(task_id))
    if response.status.value in ("cancelled", "failed"):
        rprint(f"[bold red]Task {task_id} was cancelled or produced an error[/]")
        if response.error is not None:
            rprint(f"[bold red]Error: {response.error}[/]")
    elif response.status.value == "pending":
        rprint(f"[bold cyan]Task {task_id} is still being executed[/]")
    else:
        final_output = (
            response.output[1] if response.output is not None else "No final output"
        )
        report = (
            response.output[0] if response.output is not None else "No activity report"
        )
        rprint(
            Markdown(
                f"## Final Output\n\n{final_output}\n\n## Activity Report\n\n{report}"
            )
        )


@app.command(
    name="wait-task",
    help="Poll for a task until it is completed.",
)
def wait_task(
    task_id: str,
    protocol: Annotated[
        Literal["http", "https"],
        Option(
            "--protocol",
            "-t",
            help="Protocol for the connection. Defaults to 'http'.",
        ),
    ] = "http",
    host: Annotated[
        str,
        Option(
            "--bind",
            "-b",
            help="Host to bind the server to. Defaults to 0.0.0.0",
        ),
    ] = "0.0.0.0",
    port: Annotated[
        int,
        Option(
            "--port",
            "-p",
            help="Port to bind the server to. Defaults to 8000",
        ),
    ] = 8000,
    polling_interval: Annotated[
        float,
        Option(
            "--polling-interval",
            "-i",
            help="Interval (in seconds) between a polling request and the following one. Defaults to 2 seconds.",
        ),
    ] = 2.0,
    max_attempts: Annotated[
        int,
        Option(
            "--max-attempts",
            "-m",
            help="Maximum number of polling attempts. Defaults to 900 (for a total of 30 minutes with the default polling interval).",
        ),
    ] = 900,
    server_api_key: Annotated[
        str | None,
        Option(
            "--server-key",
            help="API key to be used within the server to authorize requests. Reads from LOBSTERX_SERVER_KEY env variable if not provided.",
        ),
    ] = None,
    config_file: Annotated[
        str | None,
        Option(
            "--config",
            "-c",
            help="Config file from which to read the LobsterX server configuration. Configured options have precedence over CLI.",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        Option(
            "--verbose/--no-verbose",
            help="Whether or not to enable verbose logging.",
        ),
    ] = True,
) -> None:
    if config_file is not None:
        args = LobsterXApiConfig.load_from_config(config_file)
        port = args.port or port
        host = args.host or host
        protocol = args.protocol or protocol
    client = LobsterXClient(
        api_key=server_api_key, host=host, port=port, protocol=protocol
    )
    response = asyncio.run(
        client.poll_for_task(
            task_id,
            polling_interval=polling_interval,
            max_attempts=max_attempts,
            verbose=verbose,
        )
    )
    if response is None:
        return
    if response.status.value in ("cancelled", "failed"):
        rprint(f"[bold red]Task {task_id} was cancelled or produced an error[/]")
        if response.error is not None:
            rprint(f"[bold red]Error: {response.error}[/]")
    elif response.status.value == "pending":
        rprint(f"[bold cyan]Task {task_id} is still being executed[/]")
    else:
        final_output = (
            response.output[1] if response.output is not None else "No final output"
        )
        report = (
            response.output[0] if response.output is not None else "No activity report"
        )
        rprint(
            Markdown(
                f"## Final Output\n\n{final_output}\n\n## Activity Report\n\n{report}"
            )
        )


@app.command(
    name="cancel-task",
    help="Send a request to a LobsterX server to cancel a task.",
)
def cancel_task(
    task_id: str,
    protocol: Annotated[
        Literal["http", "https"],
        Option(
            "--protocol",
            "-t",
            help="Protocol for the connection. Defaults to 'http'.",
        ),
    ] = "http",
    host: Annotated[
        str,
        Option(
            "--bind",
            "-b",
            help="Host to bind the server to. Defaults to 0.0.0.0",
        ),
    ] = "0.0.0.0",
    port: Annotated[
        int,
        Option(
            "--port",
            "-p",
            help="Port to bind the server to. Defaults to 8000",
        ),
    ] = 8000,
    server_api_key: Annotated[
        str | None,
        Option(
            "--server-key",
            help="API key to be used within the server to authorize requests. Reads from LOBSTERX_SERVER_KEY env variable if not provided.",
        ),
    ] = None,
    config_file: Annotated[
        str | None,
        Option(
            "--config",
            "-c",
            help="Config file from which to read the LobsterX server configuration. Configured options have precedence over CLI.",
        ),
    ] = None,
) -> None:
    if config_file is not None:
        args = LobsterXApiConfig.load_from_config(config_file)
        port = args.port or port
        host = args.host or host
        protocol = args.protocol or protocol
    client = LobsterXClient(
        api_key=server_api_key, host=host, port=port, protocol=protocol
    )
    asyncio.run(client.cancel_task(task_id))
    print(f"Successfully cancelled task {task_id}.")
