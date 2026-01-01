import json

from pathlib import Path
from typing import Literal
from ..constants import TODO_FILE


def _find_git_root() -> Path | None:
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
    _todo_to_json(items, statuses)
    return "TODO list successfully created!"


def list_todos() -> str:
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
    if TODO_FILE.is_file():
        with open(TODO_FILE, "r") as f:
            data = json.load(f)
        data[item] = status
        with open(TODO_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return f"Item {item} successfully set to status {status} in your TODO list!"
    return "No TODOs registered yet. Use the `create_todos` tool to create a list of TODOs."
