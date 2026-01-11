import json

from typing import Annotated
from typing_extensions import TypedDict
from .todo import _find_git_root
from ..constants import MEMORY_FILE


class MemoryPiece(TypedDict):
    """
    Represents a single memory record with an ID, content, and relevance score.
    """

    id_: int
    content: str
    relevance: int


def write_memory(content: str, relevance: Annotated[int, ">=0,=<100"]) -> str:
    """
    Write a new memory record to the memory file.

    Args:
        content (str): The content of the memory to store.
        relevance (int): The relevance score (0-100) for the memory.
    Returns:
        str: Success message after writing the memory.
    """
    if not MEMORY_FILE.is_file():
        git_root = _find_git_root()
        if git_root is not None:
            (git_root / ".gitignore").touch()
            if (
                "\n# memory jsonl file\n.agent_memory.jsonl\n"
                not in (git_root / ".gitignore").read_text()
            ):
                with open(git_root / ".gitignore", "a") as f:
                    f.write("\n# memory jsonl file\n.agent_memory.jsonl\n")
        mem_payload = MemoryPiece(content=content, relevance=relevance, id_=0)
        with open(MEMORY_FILE, "w") as f:
            s = json.dumps(mem_payload) + "\n"
            f.write(s)
    else:
        id_ = len(MEMORY_FILE.read_text().splitlines())
        mem_payload = MemoryPiece(content=content, relevance=relevance, id_=id_)
        with open(MEMORY_FILE, "a") as f:
            s = json.dumps(mem_payload) + "\n"
            f.write(s)
    return "Memory written with success"


def read_memory(
    n_records: Annotated[int, "Number of most recent records to read"] = 10,
    relevance_threashold: Annotated[int, ">=0,=<99"] = 75,
) -> str:
    """
    Read the most recent memory records above a relevance threshold.

    Args:
        n_records (int): Number of most recent records to read.
        relevance_threashold (int): Minimum relevance score to include.
    Returns:
        str: Formatted string of memory records or a message if none exist.
    """
    if MEMORY_FILE.is_file():
        lines = MEMORY_FILE.read_text().splitlines()
        pieces: list[MemoryPiece] = []
        lines.reverse()
        for line in lines:
            loaded: MemoryPiece = json.loads(line.strip())
            if loaded["relevance"] >= relevance_threashold:
                pieces.append(loaded)
            if len(pieces) == n_records:
                break
        memory = ""
        for piece in pieces:
            memory += f"ID: {piece['id_']}; Content: {piece['content']}; Relevance: {piece['relevance']}\n"
        return memory
    else:
        return "No memories recorded yet. Please use the `write_memory` tool to record memories before reading them."
