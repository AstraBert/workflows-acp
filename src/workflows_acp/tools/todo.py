import json

from pathlib import Path
from typing import Literal
from ..constants import TODO_FILE


def _find_git_root() -> Path | None:
    """
    Find the root directory of the current git repository.

    Returns:
        Path | None: The path to the git root, or None if not found.
    """
    if not (Path.cwd() / ".git").is_dir():
        parents = Path.cwd().parents
        for parent in parents:
            if (parent / ".git").is_dir():
                return parent
        return None
    return Path.cwd()


def _todo_to_json(
    items: list[str], statuses: list[Literal["pending", "in_progress", "completed"]]
) -> None:
    """
    Write the TODO items and their statuses to a JSON file, and update .gitignore.

    Args:
        items (list[str]): List of TODO item descriptions.
        statuses (list[Literal["pending", "in_progress", "completed"]]): List of statuses for each item.
    """
    git_root = _find_git_root()
    if git_root is not None:
        (git_root / ".gitignore").touch()
        if ".todo.json\n" not in (git_root / ".gitignore").read_text():
            with open(git_root / ".gitignore", "a") as f:
                f.write("\n# todo json file\n.todo.json\n")
    todo_list: dict[str, Literal["pending", "in_progress", "completed"]] = {}
    for i, item in enumerate(items):
        todo_list[item] = statuses[i]
    with open(TODO_FILE, "w") as f:
        json.dump(todo_list, f, indent=2)


def create_todos(
    items: list[str], statuses: list[Literal["pending", "in_progress", "completed"]]
) -> str:
    """
    Create a TODO list and save it to a JSON file.

    Args:
        items (list[str]): List of TODO item descriptions.
        statuses (list[Literal["pending", "in_progress", "completed"]]): List of statuses for each item.
    Returns:
        str: Success message after creating the TODO list.
    """
    _todo_to_json(items, statuses)
    return "TODO list successfully created!"


def list_todos() -> str:
    """
    List all TODO items and their statuses in a markdown table format.

    Returns:
        str: Markdown table of TODOs or a message if none exist.
    """
    if TODO_FILE.is_file():
        with open(TODO_FILE, "r") as f:
            data = json.load(f)
        todos = "| TASK | STATUS |\n|------|------|\n"
        for k in data:
            todos += f"| {k} | {data[k]} |\n"
        return todos
    return "No TODOs registered yet. Use the `create_todos` tool to create a list of TODOs."


def update_todo(
    item: str, status: Literal["pending", "in_progress", "completed"]
) -> str:
    """
    Update the status of a TODO item.

    Args:
        item (str): The TODO item to update.
        status (Literal["pending", "in_progress", "completed"]): The new status for the item.
    Returns:
        str: Success or error message.
    """
    if TODO_FILE.is_file():
        with open(TODO_FILE, "r") as f:
            data = json.load(f)
        data[item] = status
        with open(TODO_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return f"Item {item} successfully set to status {status} in your TODO list!"
    return "No TODOs registered yet. Use the `create_todos` tool to create a list of TODOs."
