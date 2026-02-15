import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Literal

import uvicorn
from dotenv import set_key
from rich.prompt import Prompt
from typer import Option, Typer
from workflows_acp.constants import AVAILABLE_MODELS

from .api.api import create_api_app
from .api.shared import LobsterXApiConfig
from .bot import run_bot
from .constants import LOG_LEVELS

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
    if api_key is None:
        api_key = Prompt().ask(
            "API key for model provider",
            password=True,
        )
    if llama_cloud_api_key is None:
        llama_cloud_api_key = Prompt().ask("API key for LlamaCloud", password=True)
    if telegram_token is None:
        telegram_token = Prompt().ask("Bot Token for Telegram", password=True)
    dot_env = Path(".env")
    if not dot_env.exists():
        dot_env.touch()
    set_key(".env", key_to_set="LOBSTERX_LLM_PROVIDER", value_to_set=llm_provider)
    set_key(".env", key_to_set="LOBSTERX_LLM_MODEL", value_to_set=llm_model)
    set_key(".env", key_to_set="LOBSTERX_LLM_API_KEY", value_to_set=api_key)
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
            help="Origins to be allowed for CORS",
        ),
    ] = [],
    file_downloads_per_minute: Annotated[
        int | None,
        Option(
            "--file-downloads-per-minute",
            "-a",
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
            help="Config file from which to read the LobsterX server configuration.",
        ),
    ] = None,
) -> None:
    if config_file is not None:
        args = LobsterXApiConfig.load_from_config(config_file)
        app = create_api_app(**asdict(args))
    else:
        app = create_api_app(
            allow_origins=allow_origins,
            create_tasks_per_minute=create_tasks_per_minute,
            delete_tasks_per_minute=delete_tasks_per_minute,
            poll_tasks_per_minute=poll_tasks_per_minute,
            file_downloads_per_minute=file_downloads_per_minute,
            server_api_key=server_api_key,
        )
    uvicorn.run(app, host=host, port=port)
