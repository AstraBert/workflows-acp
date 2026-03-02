import asyncio
import os
from pathlib import Path
from secrets import token_urlsafe
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from lobsterx.api.api import GetTaskResponse, create_api_app
from lobsterx.api.shared import TaskRequest, TaskResponse, UploadFileResponse
from lobsterx.constants import DATA_DIR


def test_api_file_uploads(tmp_path: Path) -> None:
    with patch(
        "lobsterx.api.api._download_file_to_agentfs", new_callable=AsyncMock
    ) as mock_download:
        mock_download.return_value = None
        api_key = token_urlsafe(48)
        app = create_api_app(
            server_api_key=api_key,
            allow_origins=[],
            file_downloads_per_minute=None,
            poll_tasks_per_minute=None,
            delete_tasks_per_minute=None,
            create_tasks_per_minute=None,
        )
        client = TestClient(app)
        (tmp_path / "test.txt").write_text("hello world")
        with open(tmp_path / "test.txt", "rb") as f:
            files = ("test.txt", f, "text/plain")
            response = client.post(
                "/files",
                files={"file": files},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            assert response.status_code == 200
            payload = response.json()
            validated = UploadFileResponse.model_validate(payload)
            assert validated.new_file_path == os.path.join(DATA_DIR, "test.txt")
            mock_download.assert_awaited_once()


async def handle_prompt_mock(*args, **kwargs):
    return ("hello", "world")


async def handle_prompt_mock_cancel(*args, **kwargs):
    await asyncio.sleep(0.1)
    return ("hello", "world")


@pytest.mark.asyncio
async def test_api_create_and_get_task() -> None:
    with patch("lobsterx.api.api.handle_prompt", new_callable=AsyncMock) as mock_prompt:
        mock_prompt.side_effect = handle_prompt_mock
        api_key = token_urlsafe(48)
        app = create_api_app(
            server_api_key=api_key,
            allow_origins=[],
            file_downloads_per_minute=None,
            poll_tasks_per_minute=None,
            delete_tasks_per_minute=None,
            create_tasks_per_minute=None,
        )
        client = TestClient(app)
        json = TaskRequest(prompt="hello world").model_dump()
        response = client.post(
            "/tasks",
            json=json,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert response.status_code == 200
        payload = response.json()
        validated = TaskResponse.model_validate(payload)
        # is a UUID v4
        assert len(validated.task_id) == 36
        assert validated.task_id.count("-") == 4
        await asyncio.sleep(0.01)
        response_get = client.get(
            f"/tasks/{validated.task_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert response_get.status_code == 200
        payload = response_get.json()
        validated = GetTaskResponse.model_validate(payload)
        assert validated.output == ("hello", "world")


@pytest.mark.asyncio
async def test_api_create_and_cancel_task() -> None:
    with patch("lobsterx.api.api.handle_prompt", new_callable=AsyncMock) as mock_prompt:
        mock_prompt.side_effect = handle_prompt_mock_cancel
        api_key = token_urlsafe(48)
        app = create_api_app(
            server_api_key=api_key,
            allow_origins=[],
            file_downloads_per_minute=None,
            poll_tasks_per_minute=None,
            delete_tasks_per_minute=None,
            create_tasks_per_minute=None,
        )
        client = TestClient(app)
        json = TaskRequest(prompt="hello world").model_dump()
        response = client.post(
            "/tasks",
            json=json,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert response.status_code == 200
        payload = response.json()
        validated = TaskResponse.model_validate(payload)
        # is a UUID v4
        assert len(validated.task_id) == 36
        assert validated.task_id.count("-") == 4
        await asyncio.sleep(0.01)
        response_delete = client.delete(
            f"/tasks/{validated.task_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert response_delete.status_code == 204
        await asyncio.sleep(0.03)
        # try getting cancelled task (returns 404)
        response_get = client.get(
            f"/tasks/{validated.task_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert response_get.status_code == 404 or (
            response.status_code == 200
            and GetTaskResponse.model_validate(response_get.json()).status.value
            == "cancelled"
        )
