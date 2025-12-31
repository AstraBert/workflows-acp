from pathlib import Path
from acp.schema import (
    SessionMode,
    PermissionOption,
)

# ACP Wrapper
MODES = [
    SessionMode(
        id="bypass",
        name="bypassToolPermission",
        description="Bypass asking for tool permission, executing tools directly (not recommended, use 'askToolPermission' instead)",
    ),
    SessionMode(
        id="ask",
        name="askToolPermission",
        description="Ask for tool usage permission before executing it.",
    ),
]
PERMISSION_OPTIONS = [
    PermissionOption(kind="allow_once", name="Allow", option_id="allow"),
    PermissionOption(kind="reject_once", name="Reject", option_id="reject"),
]
VERSION = "0.1.0"
DEFAULT_MODE_ID = "ask"
AGENT_CONFIG_FILE = Path.cwd() / "agent_config.yaml"

# LLM Wrapper
DEFAULT_TASK = """
Assist the user with their requests, leveraging the tools available to you (as per the `Tools` section) and following the think -> act -> observe pattern detailed in the `Methods` section.
"""
DEFAULT_MODEL = "gemini-3-flash-preview"
AGENTS_MD = Path.cwd() / "AGENTS.md"
SYSTEM_PROMPT_STRING = """
## Main Task

You are a helpful assistant whose main task is:

```md
{{task}}
```

## Methods

In order to accomplish this task, you will be asked to:

- **Think**: reflect on the user's request and on what you have already done (available through chat history)
- **Act**: Take an action based on the current situation and informed by the chat history. The action might be:
    + A tool call (using one of the available tools, listed in the `Tools` section)
    + A question to the user (human in the loop)
    + A stop call (providing a stop reason and a final result)
- **Observe**: Following tool calls, you will observe/summarize the current situation in order to inform the thinking step about tool results and potential scenarios moving forward.

## Tools

{{tools}}
{{additional_instructions}}
"""

# MCP Wrapper
MCP_CONFIG_FILE = Path.cwd() / ".mcp.json"
