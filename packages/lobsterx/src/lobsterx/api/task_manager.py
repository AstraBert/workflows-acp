import asyncio
import functools
import uuid
from dataclasses import dataclass
from enum import Enum


class StatusEnum(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    CANCELLED = "cancelled"


@dataclass
class TaskRepr:
    status: StatusEnum
    output: tuple[str, str] | None = None
    error: str | None = None


class InMemoryTaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[tuple[str, str]]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def add_task(self, task: asyncio.Task[tuple[str, str]]) -> str:
        id_ = str(uuid.uuid4())
        async with self._lock:
            self._tasks[id_] = task
            return id_

    async def check_task(self, id_: str) -> TaskRepr | None:
        task = self._tasks.get(id_)
        if task is None:
            return task
        if task.done():
            if (e := task.exception()) is not None:
                async with self._lock:
                    self._tasks.pop(id_)
                return TaskRepr(status=StatusEnum.FAILED, error=str(e))
            result = task.result()
            async with self._lock:
                self._tasks.pop(id_)
            return TaskRepr(status=StatusEnum.SUCCESS, output=result)
        if task.cancelled() or task.cancelling():
            try:
                await task
            except asyncio.CancelledError:
                async with self._lock:
                    self._tasks.pop(id_)
                return TaskRepr(status=StatusEnum.CANCELLED)
        return TaskRepr(status=StatusEnum.PENDING)

    async def cancel_task(self, id_: str) -> None:
        task = self._tasks.get(id_)
        if task is None:
            return task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            async with self._lock:
                self._tasks.pop(id_)
            return None


@functools.lru_cache(maxsize=1)
def get_task_manager() -> InMemoryTaskManager:
    return InMemoryTaskManager()
