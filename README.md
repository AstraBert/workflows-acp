# workflows-acp

Run an agent powered by LlamaIndex Workflows over the ACP wire.

## Installation

From source:

```bash
git clone https://github.com/AstraBert/workflows-acp
cd workflows-acp
uv tool install .
```

Test installation:

```bash
wfacp --help
```

## Usage

In order to use the CLI and python API, you need a `GOOGLE_API_KEY` set in your environment:

```bash
export GOOGLE_API_KEY="my-api-key"
```

### CLI

In order to use the CLI agent, you need to provide an `agent_config.yaml` file, containing the following fields:

- `mode` ('ask' or 'bypass'): permission mode for the agent. Default is `ask`
- `tools`: list of tools (among the default ones) that the agent can use
- `model`: the LLM model that the agent should use (Gemini models only). Default is `gemini-3-flash-preview`
- `agent_task`: task that you need the agent's assistance on.

Find an example in [agent_config.yaml](./agent_config.yaml).

You can also add/modify configuration options to your existing `agent_config.yaml` with the command line app `wfacp`:

```bash
# create config file
touch agent_config.yaml
# add tool
wfacp add-tool -t read_file
# remove tool
wfacp rm-tool -t read_file
# add/modify agent task
wfacp task -t "You should assist the user with python coding"
# add/modify mode
wfacp mode -m bypass
# add/modify model
wfacp model -m gemini-3-pro-preview
```

To run the agent, use an ACP-compatible client like `toad` or Zed editor.

**With `toad`**

```bash
# install toad
curl -fsSL batrachian.ai/install | sh
# run
toad acp "wfacp run"
```

A beautiful terminal interface will open and you will be able to talk to the agent through that.

**With Zed**

Add this to your `settings.json`:

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

In this case, you will be able to interact with the agent directly in-IDE.

## Python API

Define your ACP agent by passing a specific set of tools, customizing its agent prompt or LLM model:

```python
import asyncio

from workflows_acp.acp_wrapper import start_agent
from workflows_acp.models import Tool

def add(x: int, y: int) -> int:
    return x+y

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
model = "gemini-2.5-flash"

def main() -> None:
    asyncio.run(start_agent(tools=[db_tool, add_tool], agent_task=task, llm_model=model))
```

Or load the agent from an `agent_config.yaml` file:

```python
import asyncio

from workflows_acp.acp_wrapper import start_agent

def main() -> None:
    asyncio.run(start_agent(confing_file="agent_config.yaml"))
```