import io
import os
from pathlib import Path
from secrets import token_urlsafe
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from lobsterx.api.api import create_api_app
from lobsterx.api.shared import UploadFileResponse
from lobsterx.constants import DATA_DIR


def _client() -> TestClient:
    api_key = token_urlsafe(32)
    app = create_api_app(
        server_api_key=api_key,
        allow_origins=[],
        file_downloads_per_minute=None,
        poll_tasks_per_minute=None,
        delete_tasks_per_minute=None,
        create_tasks_per_minute=None,
    )
    client = TestClient(app)
    client.api_key = api_key
    return client


def _upload(client: TestClient, name: str):
    return client.post(
        "/files",
        files={"file": (name, io.BytesIO(b"hello world"), "text/plain")},
        headers={"Authorization": f"Bearer {client.api_key}"},
    )


def test_upload_plain_name_stays_in_data_dir():
    client = _client()
    with patch(
        "lobsterx.api.api._download_file_to_agentfs", new_callable=AsyncMock
    ):
        response = _upload(client, "report.txt")
        assert response.status_code == 200
        assert UploadFileResponse.model_validate(response.json()).new_file_path == os.path.join(
            DATA_DIR, "report.txt"
        )


def test_upload_traversal_name_is_confined_to_data_dir():
    client = _client()
    with patch(
        "lobsterx.api.api._download_file_to_agentfs", new_callable=AsyncMock
    ):
        response = _upload(client, "../../evil.txt")
        assert response.status_code == 200
        assert UploadFileResponse.model_validate(response.json()).new_file_path == os.path.join(
            DATA_DIR, "evil.txt"
        )


def test_upload_absolute_name_is_confined_to_data_dir():
    client = _client()
    with patch(
        "lobsterx.api.api._download_file_to_agentfs", new_callable=AsyncMock
    ):
        response = _upload(client, "/tmp/evil.txt")
        assert response.status_code == 200
        assert UploadFileResponse.model_validate(response.json()).new_file_path == os.path.join(
            DATA_DIR, "evil.txt"
        )
