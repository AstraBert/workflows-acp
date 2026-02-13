import asyncio
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any


class StatusEnum(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    CANCELLED = "cancelled"


@dataclass
class TaskRepr:
    status: StatusEnum
    output: Any | None = None


class InMemoryTaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}

    def add_task(self, task: asyncio.Task) -> str:
        id_ = str(uuid.uuid4())
        self._tasks[id_] = task
        return id_

    async def check_task(self, id_: str) -> TaskRepr | None:
        task = self._tasks.get(id_)
        if task is None:
            return task
        if task.done():
            if (e := task.exception()) is not None:
                self._tasks.pop(id_)
                return TaskRepr(status=StatusEnum.FAILED, output=str(e))
            result = task.result()
            self._tasks.pop(id_)
            return TaskRepr(status=StatusEnum.SUCCESS, output=result)
        if task.cancelled() or task.cancelling():
            try:
                await task
            except asyncio.CancelledError:
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
            self._tasks.pop(id_)
            return None
