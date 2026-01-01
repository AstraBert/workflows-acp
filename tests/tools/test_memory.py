import pytest
import os
import json

from pathlib import Path
from workflows_acp.tools.memory import write_memory, read_memory


def setup_folder(tmp_path: Path):
    os.makedirs(tmp_path / ".git")
    (tmp_path / ".gitignore").touch()


def test_write_memory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = write_memory("hello", 10)
    assert result == "Memory written with success"
    assert (tmp_path / ".agent_memory.jsonl").is_file()
    lines = (tmp_path / ".agent_memory.jsonl").read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0].strip()) == {
        "id_": 0,
        "content": "hello",
        "relevance": 10,
    }
    assert (
        tmp_path / ".gitignore"
    ).read_text() == "\n# memory jsonl file\n.agent_memory.jsonl\n"
    result = write_memory("hello1", 100)
    assert result == "Memory written with success"
    assert (tmp_path / ".agent_memory.jsonl").is_file()
    lines = (tmp_path / ".agent_memory.jsonl").read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1].strip()) == {
        "id_": 1,
        "content": "hello1",
        "relevance": 100,
    }


def test_read_memory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = read_memory()
    assert (
        result
        == "No memories recorded yet. Please use the `write_memory` tool to record memories before reading them."
    )
    write_memory("hello1", 100)
    write_memory("hello2", 75)
    write_memory("hello3", 20)
    write_memory("hello", 10)
    result = read_memory()
    assert (
        result
        == "ID: 1; Content: hello2; Relevance: 75\nID: 0; Content: hello1; Relevance: 100\n"
    )
    result = read_memory(n_records=1, relevance_threashold=5)
    assert result == "ID: 3; Content: hello; Relevance: 10\n"
