import os
import pytest
from pathlib import Path

from agentfs_sdk import AgentFS
from workflows_acp.tools.agentfs import (
    read_file_agentfs,
    write_file_agentfs,
    edit_file_agentfs,
    configure_agentfs,
    load_all_files,
    _is_accessible_path,
)


def setup_folder(tmp_path: Path) -> None:
    files = [
        "test.txt",
        "test1.txt",
        "test2.txt",
        "hello/hello.txt",
        "hello2/hello.txt",
    ]
    dirs = [".git", "hello", "hello1", "hello2"]
    for d in dirs:
        os.makedirs(os.path.join(str(tmp_path), d))
    for i, file in enumerate(files):
        path = os.path.join(str(tmp_path), file)
        with open(path, "w") as f:
            f.write(f"Test {i}")


@pytest.mark.asyncio
async def test_configure_agentfs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path)
    monkeypatch.chdir(tmp_path)
    agentfs = await configure_agentfs()
    assert isinstance(agentfs, AgentFS)
    assert (tmp_path / "agent.db").exists()
    assert (tmp_path / ".gitignore").exists()
    assert "\n# agentfs database\nagent.db*\n" in (tmp_path / ".gitignore").read_text()


@pytest.mark.asyncio
async def test_load_all_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path)
    monkeypatch.chdir(tmp_path)
    await load_all_files(["hello1", "hello2"], ["test1.txt", "test2.txt"])
    assert (tmp_path / "agent.db").exists()
    assert (tmp_path / ".gitignore").exists()
    assert "\n# agentfs database\nagent.db*\n" in (tmp_path / ".gitignore").read_text()
    agentfs = await configure_agentfs()
    assert await _is_accessible_path(
        agentfs, str((tmp_path / "test.txt").resolve()), "file"
    )
    assert await _is_accessible_path(
        agentfs, str((tmp_path / "hello").resolve()), "dir"
    )
    assert not await _is_accessible_path(
        agentfs, str((tmp_path / "test1.txt").resolve()), "file"
    )
    assert not await _is_accessible_path(
        agentfs, str((tmp_path / "hello1").resolve()), "dir"
    )
    assert not await _is_accessible_path(
        agentfs, str((tmp_path / "test2.txt").resolve()), "file"
    )
    assert not await _is_accessible_path(
        agentfs, str((tmp_path / "hello2").resolve()), "dir"
    )
    assert not await _is_accessible_path(
        agentfs, str((tmp_path / "hello2/hello.txt").resolve()), "file"
    )


@pytest.mark.asyncio
async def test_read_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path)
    monkeypatch.chdir(tmp_path)
    await load_all_files(["hello1", "hello2"], ["test1.txt", "test2.txt"])
    result = await read_file_agentfs(str((tmp_path / "test.txt").resolve()))
    assert result.strip() == "Test 0"
    result = await read_file_agentfs(str((tmp_path / "hello" / "hello.txt").resolve()))
    assert result.strip() == "Test 3"
    result = await read_file_agentfs(str((tmp_path / "hello2/hello.txt").resolve()))
    assert result == "No such file: " + str((tmp_path / "hello2/hello.txt").resolve())


@pytest.mark.asyncio
async def test_write_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path)
    monkeypatch.chdir(tmp_path)
    await load_all_files(["hello1", "hello2"], ["test1.txt", "test2.txt"])
    result = await write_file_agentfs(
        str((tmp_path / "hello.txt").resolve()), "hello there", False
    )
    assert result == "File written with success"
    agentfs = await configure_agentfs()
    assert await _is_accessible_path(
        agentfs, str((tmp_path / "hello.txt").resolve()), "file"
    )
    content = await read_file_agentfs(str((tmp_path / "hello.txt").resolve()))
    assert content == "hello there"
    result = await write_file_agentfs(
        str((tmp_path / "hello.txt").resolve()), "hello there 1", False
    )
    assert (
        result
        == "File "
        + str((tmp_path / "hello.txt").resolve())
        + " already exist and overwrite is set to False. Cannot proceed"
    )
    content = await read_file_agentfs(str((tmp_path / "hello.txt").resolve()))
    assert content == "hello there"


@pytest.mark.asyncio
async def test_edit_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_folder(tmp_path)
    monkeypatch.chdir(tmp_path)
    await load_all_files(["hello1", "hello2"], ["test1.txt", "test2.txt"])
    result = await write_file_agentfs(
        str((tmp_path / "hello.txt").resolve()), "hello there", False
    )
    result = await edit_file_agentfs(
        str((tmp_path / "hello.txt").resolve()), "there", "there1"
    )
    assert result == "File edited with success"
    content = await read_file_agentfs(str((tmp_path / "hello.txt").resolve()))
    assert content == "hello there1"
    result = await edit_file_agentfs(
        str((tmp_path / "hello.txt").resolve()), "e", "a", 1
    )
    content = await read_file_agentfs(str((tmp_path / "hello.txt").resolve()))
    assert content == "hallo there1"
    result = await edit_file_agentfs(
        str((tmp_path / "hello2/hello.txt").resolve()), "1", "2"
    )
    assert result == "No such file: " + str((tmp_path / "hello2/hello.txt").resolve())
