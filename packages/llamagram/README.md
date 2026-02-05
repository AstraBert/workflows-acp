# LlamaGram

LlamaGram is an AI agent inspired by [OpenClaw](https://openclaw.ai) (formerly known as MoltBot or ClawdBot), which focuses on document-related tasks.

It runs as a Telegram bot as comes with a CLI interface to set up the necessary environment variables.

## Prerequisites

- Python (if setting up the bot natively, preferably with `uv`) or Docker (if deploying with Docker)
- A Telegram Bot Token, in order to connect to Telegram. Follow [this guide](https://core.telegram.org/bots/tutorial) on how to create your Telegram bot with BotFather.
- A LlamaCloud API key, in order to give LlamaGram document-processing capabilities. Sign up on LlamaCloud [here](https://cloud.llamaindex.ai/signup).
- An API key for Google, OpenAI or Anthropic (you can choose one among the three or swap between different providers)

## Installation

Install the bot natively:

```bash
# uv (recommended)
uv tool install llamagram --prerelease=allow
# pip
pip install llamagram
```

Pull the docker image (only works for AMD64-compatible platforms):

```bash
docker pull ghcr.io/astrabert/llamagram:main
```

## Setup

Through environment variables, you can customize the setup of LlamaGram:

- `LLAMAGRAM_LLM_PROVIDER`: LLM provider (choose between `google`, `anthropic` and `openai`). Default is `openai`
- `LLAMAGRAM_LLM_MODEL`: LLM model (choose among [available models](../../README.md#available-llm-models)). Default is `gpt-4.1`

You then need to set three required env variables:

- `LLAMAGRAM_LLM_API_KEY`: API key for the LLM (you can also use `OPENAI_API_KEY`, `GOOGLE_API_KEY` or `ANTHROPIC_API_KEY`, depending on the provider).
- `TELEGRAM_BOT_TOKEN`: token for the Telegram bot
- `LLAMA_CLOUD_API_KEY`: API key for LlamaCloud

You can use the setup wizard to configure LlamaGram interactively on the terminal:

```bash
llamagram setup --interactive
```

Or pass options from CLI:

```bash
llamagram setup --provider google \
    --model gemini-3-flash-preview \
    --api-key $GOOGLE_API_KEY \
    --llama-cloud-key $LLAMA_CLOUD_API_KEY \
    --telegram-token $TELEGRAM_BOT_TOKEN
```

This will create a `.env` file with the necessary variables, which will be loaded by LlamaGram at runtime (make sure not to share it with anyone).

## Run

Run LlamaGram as a CLI app:

```bash
llamagram run 
```

You can set the `--log-level` option, if you wish to have more or less logging.

Run LlamaGram in a Docker container referencing a `.env` file:

```bash
docker run ghcr.io/astrabert/llamagram:main --env-file=".env"
```

Or, setting env varaibles directly (not recommended):

```bash
docker run ghcr.io/astrabert/llamagram:main \
    --env="LLAMAGRAM_LLM_PROVIDER=openai" \
    --env="LLAMAGRAM_LLM_MODEL=gpt-4.1"\
    --env="LLAMAGRAM_LLM_API_KEY=sk-xxx" \
    --env="LLAMA_CLOUD_API_KEY=llx-xxx" \
    --env="TELEGRAM_BOT_TOKEN=tok-xxx"
```

## Use as a Telegram Bot

When on Telegram, you can perform two actions:

- Sending PDF files, which will be downloaded by the bot
- Sending text messages, which will work as prompts for the bot to start a new task

> _With `/start` command, you will have a welcome message explaining how to use the bot_

## How LlamaGram Works

LlamaGram is a generalist AI agent based on three main principles:

- [LlamaIndex Agent Workflows](https://github.com/run-llama/workflows-py): a powerful workflow engine that allows event-driven, stepwise execution of specific tasks and functions. LlamaGram uses a cyclic workflow to go through thinking, tool-calling and observing repeatedly until it produces its final output.
- Structured outputs: the LLM underlying the agent is forced to produce JSON outputs that comply with certain schemas (a tool call, a thought, an observation...): outputs are produced informed by the previous chat history, and based on context about available tools and specific tasks the agent has to perform.
- Security by design: the agent does not have access to your real filesystem, but it does have access to a virtualized copy of it provided through [AgentFS](https://github.com/tursodatabase/agentfs). PDFs sent over Telegram are also not downloaded into your real filesystem, but written within AgentFS. Files such as `.env`s or other popular credential files (`.npmrc`, `.pypirc`, `.netrc`) are excluded from the virtual filesystem, and thus unaccessible to the agent. The agent cannot use bash commands (it has access to filesystem-based tools like read/write/edit/grep/glob for AgentFS) to avoid it being able to perform destructive or vulnerable operations.

Here is what happens when you send a prompt to LlamaGram:

![Flowchart LlamaGram](./assets/flowchart_llamagram.png)

Along with the final response, the agent will also send you a report of everything it did during its session as a markdown file (namedd `session-<random-id>-report.md`).

## License

This package is provided under [MIT License](./LICENSE)

## Contributing

For contributions, refer to the [contributing guide](../../CONTRIBUTING.md)
