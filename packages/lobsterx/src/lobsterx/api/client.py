import os
from mimetypes import guess_type
from typing import Literal

from httpx import AsyncClient

from .shared import (
    GetTaskResponse,
    TaskRequest,
    TaskResponse,
    UploadFileResponse,
    get_server_key_from_env,
    validate_api_key,
)


class LobsterXClient:
    def __init__(
        self,
        api_key: str | None,
        host: str,
        port: int,
        protocol: Literal["http", "https"],
    ) -> None:
        self.base_url = f"{protocol}://{host}:{port}"
        self.api_key = api_key or get_server_key_from_env()
        if self.api_key is None:
            raise ValueError(
                "API key not provided and `LOBSTERX_SERVER_KEY` not found within the current environment"
            )
        if not validate_api_key(self.api_key):
            raise ValueError(
                "API key should be an a string of letters, numbers, hyphens and underscores, with a minimum length of 32."
            )

    async def upload_file(self, file_path: str) -> str:
        async with AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=600,
        ) as client:
            with open(file_path, "rb") as f:
                mimetype, _ = guess_type(file_path)
                file_type = mimetype or "application/pdf"
                file = (os.path.basename(file_path), f, file_type)
                response = await client.post("/files", files={"file": file})
                response.raise_for_status()
                payload = response.json()
                validated = UploadFileResponse.model_validate(payload)
                return validated.new_file_path

    async def create_task(self, prompt: str) -> str:
        async with AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=600,
        ) as client:
            payload = TaskRequest(prompt=prompt).model_dump()
            response = await client.post("/tasks", json=payload)
            response.raise_for_status()
            json_response = response.json()
            validated = TaskResponse.model_validate(json_response)
            return validated.task_id

    async def get_task(self, task_id: str) -> GetTaskResponse:
        async with AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=600,
        ) as client:
            response = await client.get(f"/tasks/{task_id}")
            response.raise_for_status()
            json_response = response.json()
            return GetTaskResponse.model_validate(json_response)

    async def cancel_task(self, task_id: str) -> None:
        async with AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=600,
        ) as client:
            response = await client.delete(f"/tasks/{task_id}")
            response.raise_for_status()
