from pathlib import Path

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
    ".env.local",
    ".env.production",
    ".env.staging",
    ".npmrc",
    ".netrc",
    ".pypirc",
    "agent.db",
    "agent.db-wal",
    "uv.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
]
DATA_DIR = Path("downloads")
AGENT_TASK = """
You should assist the user on document-related tasks.

You have read and write access to the filesystem, and you should use that to retrieve relevant documents for the user's request, and, once they are gathered:
- If the documents are in plain text format (text, markdown, JSON, YAML...), you should read them normally
- If they are unstructured documents (PDF, presentations, word documents, e.g.), you should use your parsing, structured data extraction and classification tools

You should use memory tools as much as you can, so that you can persist previous interaction with your user.
TODO-tracking tools should be used as well, but only with complex, multi-step tasks.
"""
SPECIAL_CHARS = [
    "\\",
    "_",
    "*",
    "[",
    "]",
    "(",
    ")",
    "~",
    "`",
    ">",
    "<",
    "&",
    "#",
    "+",
    "-",
    "=",
    "|",
    "{",
    "}",
    ".",
    "!",
]
