from pathlib import Path
from typing import Literal
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
AGENT_CONFIG_FILE = Path("agent_config.yaml")

# LLM Wrapper
DEFAULT_TASK = """
Assist the user with their requests, leveraging the tools available to you (as per the `Tools` section) and following the think -> act -> observe pattern detailed in the `Methods` section.
"""
DEFAULT_GOOGLE_MODEL = "gemini-3-flash-preview"
DEFAULT_ANTHROPIC_MODEL = "claude-opus-4-5"
DEFAULT_OPENAI_MODEL = "gpt-4.1"
DEFAULT_MODEL = {
    "google": DEFAULT_GOOGLE_MODEL,
    "anthropic": DEFAULT_ANTHROPIC_MODEL,
    "openai": DEFAULT_OPENAI_MODEL,
}
AVAILABLE_MODELS: dict[str, Literal["google", "anthropic", "openai"]] = {
    "gemini-2.5-flash": "google",
    "gemini-2.5-flash-lite": "google",
    "gemini-2.5-pro": "google",
    "gemini-3-flash-preview": "google",
    "gemini-3-pro-preview": "google",
    "claude-opus-4-5": "anthropic",
    "claude-sonnet-4-5": "anthropic",
    "claude-haiku-4-5": "anthropic",
    "claude-opus-4-1": "anthropic",
    "claude-sonnet-4-0": "anthropic",
    "gpt-4.1": "openai",
    "gpt-5": "openai",
    "gpt-5.1": "openai",
    "gpt-5.2": "openai",
}

AGENTS_MD = Path("AGENTS.md")
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
MCP_CONFIG_FILE = Path(".mcp.json")

# Tools
TODO_FILE = Path(".todo.json")
MEMORY_FILE = Path(".agent_memory.jsonl")
AGENTFS_FILE = Path("agent.db")
DEFAULT_TO_AVOID = [
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "wheels",
]
DEFAULT_TO_AVOID_FILES = [
    ".env",
    "agent.db",
    "agent.db-wal",
    "uv.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
]
