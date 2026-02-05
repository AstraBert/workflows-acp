import asyncio
from pathlib import Path

import pytest

from llamagram.tools.caching import FileContentCache


def test_cache_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cache = FileContentCache()
    assert cache._ttl == 60 * 60 * 24
    assert (tmp_path / ".llamagram" / "cache").is_dir()


@pytest.mark.asyncio
async def test_cache_set_get(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("Hello World")
    cache = FileContentCache()
    await cache.set(
        "test.txt",
        "Hello World",
    )
    result = await cache.get("test.txt")
    assert result == "Hello World"


@pytest.mark.asyncio
async def test_cache_set_get_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("Hello World")
    cache = FileContentCache()
    cache._ttl = 0.05
    await cache.set(
        "test.txt",
        "Hello World",
    )
    result = await cache.get("test.txt")
    assert result == "Hello World"
    await asyncio.sleep(0.1)
    result = await cache.get("test.txt")
    assert result is None
