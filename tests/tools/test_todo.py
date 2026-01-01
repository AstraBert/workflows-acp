import pytest
import os
import json

from pathlib import Path
from workflows_acp.tools.todo import (
    _find_git_root,
    list_todos,
    create_todos,
    update_todo,
)


def setup_folder(tmp_path: Path):
    os.makedirs(tmp_path / ".git")
    (tmp_path / ".gitignore").touch()


def test_find_git_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path=tmp_path)
    monkeypatch.chdir(tmp_path)
    git_root = _find_git_root()
    assert str(git_root) == str(tmp_path)


def test_create_todos(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path=tmp_path)
    monkeypatch.chdir(tmp_path)
    items = ["Do something", "Do something else", "Done something"]
    statuses = ["pending", "in_progress", "completed"]
    result = create_todos(items=items, statuses=statuses)  # type: ignore
    assert result == "TODO list successfully created!"
    assert json.loads((tmp_path / ".todo.json").read_text()) == {
        "Do something": "pending",
        "Do something else": "in_progress",
        "Done something": "completed",
    }
    assert (tmp_path / ".gitignore").read_text() == "\n# todo json file\n.todo.json\n"
    items += ["Hello"]
    statuses += ["in_progress"]
    result = create_todos(items=items, statuses=statuses)  # type: ignore
    assert result == "TODO list successfully created!"
    assert json.loads((tmp_path / ".todo.json").read_text()) == {
        "Do something": "pending",
        "Do something else": "in_progress",
        "Done something": "completed",
        "Hello": "in_progress",
    }
    assert (tmp_path / ".gitignore").read_text().count(
        "\n# todo json file\n.todo.json\n"
    ) == 1


def test_list_todos(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path=tmp_path)
    monkeypatch.chdir(tmp_path)
    assert (
        list_todos()
        == "No TODOs registered yet. Use the `create_todos` tool to create a list of TODOs."
    )
    items = ["Do something", "Do something else", "Done something"]
    statuses = ["pending", "in_progress", "completed"]
    create_todos(items=items, statuses=statuses)  # type: ignore
    assert (
        list_todos()
        == "| TASK | STATUS |\n|------|------|\n| Do something | pending |\n| Do something else | in_progress |\n| Done something | completed |\n"
    )


def test_update_todo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path=tmp_path)
    monkeypatch.chdir(tmp_path)
    assert (
        update_todo("Do something", "completed")
        == "No TODOs registered yet. Use the `create_todos` tool to create a list of TODOs."
    )
    items = ["Do something", "Do something else", "Done something"]
    statuses = ["pending", "in_progress", "completed"]
    create_todos(items=items, statuses=statuses)  # type: ignore
    result = update_todo("Do something", "completed")
    assert (
        result
        == "Item Do something successfully set to status completed in your TODO list!"
    )
    assert json.loads((tmp_path / ".todo.json").read_text()) == {
        "Do something": "completed",
        "Do something else": "in_progress",
        "Done something": "completed",
    }
    result = update_todo("Start this", "pending")
    assert (
        result
        == "Item Start this successfully set to status pending in your TODO list!"
    )
    assert json.loads((tmp_path / ".todo.json").read_text()) == {
        "Do something": "completed",
        "Do something else": "in_progress",
        "Done something": "completed",
        "Start this": "pending",
    }
