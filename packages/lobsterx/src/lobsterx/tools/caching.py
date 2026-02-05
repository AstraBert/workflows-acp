import asyncio
import functools
from pathlib import Path
from typing import cast

from diskcache import Cache as DiskCache


class FileContentCache:
    def __init__(self) -> None:
        self._cache = DiskCache(directory=".lobsterx/cache")
        self._ttl: float = 60 * 60 * 24  # one day

    async def set(
        self,
        file_path: str,
        content: str,
    ) -> None:
        file_path = str(Path(file_path).resolve())
        await asyncio.to_thread(
            self._cache.set, key=file_path, value=content, expire=self._ttl
        )

    async def get(
        self,
        file_path: str,
    ) -> str | None:
        file_path = str(Path(file_path).resolve())
        content = await asyncio.to_thread(self._cache.get, key=file_path)
        return cast(str | None, content)


@functools.lru_cache(maxsize=1)
def get_cache() -> FileContentCache:
    return FileContentCache()
