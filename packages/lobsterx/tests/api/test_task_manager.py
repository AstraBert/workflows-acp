import asyncio

import pytest

from lobsterx.api.task_manager import InMemoryTaskManager


async def hello_world() -> tuple[str, str]:
    await asyncio.sleep(0.02)
    return "hello", "world"


async def throws_error() -> tuple[str, str]:
    await asyncio.sleep(0.02)
    raise ValueError("An error occurred")


def test_task_manager_init() -> None:
    manager = InMemoryTaskManager()
    assert len(manager._tasks) == 0
    assert isinstance(manager._lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_task_manager_add() -> None:
    manager = InMemoryTaskManager()
    task = asyncio.create_task(hello_world())
    task_id = await manager.add_task(task)
    assert task_id in manager._tasks
    await asyncio.sleep(0.03)
    t = manager._tasks.get(task_id)
    assert isinstance(t, asyncio.Task)
    assert t.done()
    result = t.result()
    assert result == ("hello", "world")


@pytest.mark.asyncio
async def test_task_manager_check() -> None:
    manager = InMemoryTaskManager()
    task = asyncio.create_task(hello_world())
    task_id = await manager.add_task(task)
    result = await manager.check_task(task_id)
    assert result is not None
    assert result.status.value == "pending"
    await asyncio.sleep(0.03)
    result_done = await manager.check_task(task_id)
    assert result_done is not None
    assert result_done.status.value == "success"
    assert result_done.output == ("hello", "world")
    assert result_done.error is None
    assert task_id not in manager._tasks  # tasks has been popped off of the dict


@pytest.mark.asyncio
async def test_task_manager_check_with_error() -> None:
    manager = InMemoryTaskManager()
    task = asyncio.create_task(throws_error())
    task_id = await manager.add_task(task)
    result = await manager.check_task(task_id)
    assert result is not None
    assert result.status.value == "pending"
    await asyncio.sleep(0.03)
    result_done = await manager.check_task(task_id)
    assert result_done is not None
    assert result_done.status.value == "failed"
    assert result_done.output is None
    assert result_done.error == "An error occurred"
    assert task_id not in manager._tasks  # tasks has been popped off of the dict


@pytest.mark.asyncio
async def test_task_manager_cancel() -> None:
    manager = InMemoryTaskManager()
    task = asyncio.create_task(hello_world())
    task_id = await manager.add_task(task)
    await manager.cancel_task(task_id)
    assert task_id not in manager._tasks  # tasks has been popped off of the dict
