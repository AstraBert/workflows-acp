# workflows-acp

Run an agent powered by LlamaIndex Workflows over the ACP wire.

## Installation

To install from registry:

```bash
# with pip
pip install workflows-acp
# with uv
uv add workflows-acp
# with uv - tool install
uv tool install workflows-acp
```

To install from source:

```bash
git clone https://github.com/AstraBert/workflows-acp
cd workflows-acp
uv tool install .
```

To verify the installation:

```bash
wfacp --help
```

## Usage

To use the CLI and Python API, set your `GOOGLE_API_KEY`/`OPENAI_API_KEY`/`ANTHROPIC_API_KEY` (based on your [LLM provider](#available-llm-models)) in the environment:

```bash
export GOOGLE_API_KEY="my-api-key"
```

To reduce logging noise from [mcp-use](https://mcp-use.com)'s telemetry, run:

```bash
export MCP_USE_ANONYMIZED_TELEMETRY=false
```

### CLI

To use the CLI agent, provide an `agent_config.yaml` file with the following fields:

- `mode` ('ask' or 'bypass'): Permission mode for the agent. Default is `ask`.
- `tools`: List of tools (from the default set) available to the agent.
- `model`: The LLM model for the agent (Gemini models only). Default is `gemini-3-flash-preview`.
- `agent_task`: The task for which you need the agent's assistance.

See the example in [agent_config.yaml](./agent_config.yaml).

If you wish to provide additional instructions to the agent (e.g. context on the current project, best practices, coding style rules...) you can add these instructions to an **AGENTS.md** file in the directory the agent is working in.

You can add or modify configuration options in your `agent_config.yaml` using the `wfacp` CLI:

```bash
# Add a tool
wfacp add-tool -t read_file
# Remove a tool
wfacp rm-tool -t read_file
# Add or modify the agent task
wfacp task -t "You should assist the user with python coding"
# Set or change the mode
wfacp mode -m bypass
# Set or change the model
wfacp model -m gemini-3-pro-preview
```

`workflows-acp` supports a [list of models](#available-llm-models) provided by OpenAI, Anthropic and Google.

To use the agent with MCP servers, create a `.mcp.json` file with server definitions:

```json
{
  "mcpServers": {
    "with-stdio": {
      "command": "npx",
      "args": [
        "@mcp/server",
        "start"
      ]
    },
    "with-http": {
      "url": "https://example.com/mcp"
    }
  }
}
```

For servers using `stdio`, specify a `command` and optionally a list of `args` and an `env` for the MCP process. For servers using `http`, specify a `url` and optionally add `headers` for requests.

See a complete example in [`.mcp.json`](./.mcp.json).

MCP configuration can also be managed via CLI:

```bash
# Add a stdio MCP server
wfacp add-mcp --name test --transport stdio --command 'npx @mcp/server arg1 arg2' --env "PORT=3000" --env "TELEMETRY=false"
# Add an HTTP MCP server
wfacp add-mcp --name search --transport http --url https://www.search.com/mcp --header "Authorization=Bearer $API_KEY" --header "X-Hello-World=Hello world!"
# Remove a server
wfacp rm-mcp --name search
```

If you wish to disable MCP usage when running the agent, you can do so by running:

```bash
wfacp run --no-mcp
```

You can also use the agent with an AgentFS virtual filesystem instead of your real one. While you can load all the files on-the-fly when running the agent, it is advisable to use the `load-agentfs` command:

```bash
wfacp load-agentfs
# skipping specific files
wfacp load-agentfs --skip-file uv.lock --skip-file go.sum
# skipping specific directories
wfacp load-agentfs --skip-dir .git --skip-dir .venv
```

When running the agent, enable AgentFS in this way:

```bash
wfacp run --agentfs
# skipping specific files
wfactp run --agentfs --agentfs-skip-file uv.lock --agentfs-skip-file go.sum
# skipping specific directories
wfactp run --agentfs --agentfs-skip-dir .git --agentfs-skip-dir .venv
```

Read more about AgentFS in the [dedicated section](#agentfs-integration).

To run the agent, use an ACP-compatible client such as `toad` or Zed editor.

**With `toad`**

```bash
# Install toad
curl -fsSL batrachian.ai/install | sh
# Run
toad acp "wfacp run"
```

A terminal interface will open, allowing you to interact with the agent.

**With Zed**

Add the following to your `settings.json`:

```json
{
  "agent_servers": {
    "AgentWorkflow": {
      "command": "wfacp",
      "args": [
        "run"
      ]
    }
  }
}
```

You can then interact with the agent directly in the IDE.

### Available LLM Models

The following LLM models are supported and can be selected in your `agent_config.yaml` or via CLI/python API:

**Google**
- gemini-2.5-flash
- gemini-2.5-flash-lite
- gemini-2.5-pro
- gemini-3-flash-preview
- gemini-3-pro-preview

**Anthropic**
- claude-opus-4-5
- claude-sonnet-4-5
- claude-haiku-4-5
- claude-opus-4-1
- claude-sonnet-4-0

**OpenAI**
- gpt-4.1
- gpt-5
- gpt-5.1
- gpt-5.2

### Available tools by default

The following tools are available by default and can be enabled in your `agent_config.yaml`:

- `describe_dir_content`: Describes the contents of a directory, listing files and subfolders. (available with AgentFS integration)
- `read_file`: Reads the contents of a file and returns it as a string. (available with AgentFS integration)
- `grep_file_content`: Searches for a regex pattern in a file and returns all matches. (available with AgentFS integration)
- `glob_paths`: Finds files in a directory matching a glob pattern. (available with AgentFS integration)
- `write_file`: Writes content to a file, with an option to overwrite. (available with AgentFS integration)
- `edit_file`: Edits a file by replacing occurrences of a string with another string. (available with AgentFS integration)
- `execute_command`: Executes a shell command with arguments. Optionally waits for completion.
- `bash_output`: Retrieves the stdout and stderr output of a previously started background process by PID.
- `write_memory`: Writes a memory with content and relevance score to persistent storage.
- `read_memory`: Reads the most recent and relevant memory records from persistent storage.
- `create_todos`: Creates a TODO list with specified items and statuses.
- `list_todos`: Lists all TODO items and their statuses.
- `update_todo`: Updates the status of a TODO item.

### AgentFS Integration

`wfacp` integrates with [AgentFS](https://github.com/tursodatabase/agentfs) (a virtual filesystem designed for coding agent) with the following steps:

1. **Initialization**: An `agent.db` file is creted
2. **Loading**: All the files in the current directory, with the exception of those you explicitly excluded, will be loaded to the `agent.db` database
3. **Tools**: Instead of loading the normal set of tools, the tools related to filesystem operations are loaded from [agentfs.py](./src/workflows_acp/tools/agentfs.py).

Now every filesystem operation performed by the agent is done on the virtual filesystem, and not on your real one, allowing the agent to perform dangerous and potentially damaging operations without affecting your actual files. 

### Examples

Find more examples of the CLI and Python API usage in the [examples](./examples/) folder.

### Python API

Define your ACP agent by specifying tools, customizing the agent prompt, or selecting an LLM model:

```python
import asyncio

from workflows_acp.acp_wrapper import start_agent
from workflows_acp.models import Tool

def add(x: int, y: int) -> int:
    return x + y

async def query_database(query: str) -> str:
    result = await db.query(query).fetchall()
    return "\n".join(result)

add_tool = Tool(
    name="add",
    description="Add two integers together",
    fn=add,
)
db_tool = Tool(
    name="query_database",
    description="Query a database with SQL syntax",
    fn=query_database,
)

task = "You are an accountant who needs to help the user with their expenses (`expenses` table in the database), and you can do so by using the `query_database` tool and perform mathematical operations with the `add` tool"
model = "gpt-5.2" # you can use any model among the supported ones

def main() -> None:
    asyncio.run(start_agent(tools=[db_tool, add_tool], agent_task=task, llm_model=model, use_mcp=False))
```

Or load the agent from an `agent_config.yaml` file:

```python
import asyncio

from workflows_acp.acp_wrapper import start_agent

def main() -> None:
    asyncio.run(start_agent(from_config_file=True, use_mcp=False))
```

You can also configure MCP servers:

```python
import asyncio
import os

from workflows_acp.acp_wrapper import start_agent
from workflows_acp.mcp_wrapper import McpServersConfig, HttpMcpServer, StdioMcpServer

stdio_server = StdioMcpServer(command="npx", args=["@test/mcp", "helloworld"], env=None)
http_server = HttpMcpServer(url="https://example.com/mcp", headers={"Authorization": "Bearer " + os.getenv("API_KEY", "")})
servers_config = McpServersConfig(mcpServers={
  "with-stdio": stdio_server,
  "with-http": http_server,
})

def main() -> None:
    asyncio.run(start_agent(from_config_file=True, use_mcp=True, mcp_config=servers_config))
```

Or load from a `.mcp.json` file:

```python
import asyncio

from workflows_acp.acp_wrapper import start_agent

def main() -> None:
    # Automatically finds .mcp.json, loads, and validates the config
    asyncio.run(start_agent(from_config_file=True, use_mcp=True))
```

You can also integrate with AgentFS:

```python
import asyncio

from workflows_acp.acp_wrapper import start_agent

def main() -> None:
    # Automatically loads all the files to AgentFS
    asyncio.run(
      start_agent(
        from_config_file=True, 
        use_agentfs=True, 
        agentfs_skip_files=[".env", "uv.lock"], 
        agentfs_skip_dirs=[".venv", ".git", "__pycache__"]
      )
    )
```

