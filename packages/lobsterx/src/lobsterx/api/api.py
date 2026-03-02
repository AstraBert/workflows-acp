import asyncio
import mimetypes
import os

from fastapi import FastAPI, HTTPException
from fastapi.datastructures import UploadFile
from fastapi.param_functions import Depends, File
from fastapi_throttle import RateLimiter
from random_name import generate_name
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from ..constants import DATA_DIR
from ..utils import _download_file_to_agentfs, handle_prompt
from .auth import LobsterXAuthentication, on_auth_error
from .shared import (
    GetTaskResponse,
    TaskRequest,
    TaskResponse,
    UploadFileResponse,
    get_server_key_from_env,
    validate_api_key,
)
from .task_manager import get_task_manager

DEFAULT_FILE_DOWNLOADS_PER_MINUTE = 300
DEFAULT_TASKS_PER_MINUTE = 60
DEFAULT_DELETE_TASKS_PER_MINUTE = 60
DEFAULT_POLL_TASKS_PER_MINUTE = 300


def _get_file_name(document: UploadFile) -> str:
    extension = (
        mimetypes.guess_extension(document.content_type or "application/pdf") or ".pdf"
    )
    if document.filename is None:
        return generate_name() + extension
    else:
        if document.filename.endswith(extension):
            return document.filename
        return document.filename + extension


def create_api_app(
    allow_origins: list[str],
    file_downloads_per_minute: int | None,
    create_tasks_per_minute: int | None,
    delete_tasks_per_minute: int | None,
    poll_tasks_per_minute: int | None,
    server_api_key: str | None,
) -> FastAPI:
    app = FastAPI()

    file_downloads_per_minute = (
        file_downloads_per_minute or DEFAULT_FILE_DOWNLOADS_PER_MINUTE
    )
    tasks_per_minute = create_tasks_per_minute or DEFAULT_TASKS_PER_MINUTE
    delete_tasks_per_minute = delete_tasks_per_minute or DEFAULT_DELETE_TASKS_PER_MINUTE
    poll_tasks_per_minute = poll_tasks_per_minute or DEFAULT_POLL_TASKS_PER_MINUTE
    api_key = server_api_key or get_server_key_from_env()
    if api_key is None:
        raise ValueError(
            "API key not provided and `LOBSTERX_SERVER_KEY` not found within the current environment"
        )

    if not validate_api_key(api_key):
        raise ValueError(
            "API key should be an a string of letters, numbers, hyphens and underscores, with a minimum length of 32."
        )

    app.add_middleware(
        CORSMiddleware,  # type: ignore[invalid-argument-type]
        allow_origins=allow_origins,
        allow_methods=["POST", "GET", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )

    app.add_middleware(
        AuthenticationMiddleware,  # type: ignore[invalid-argument-type]
        backend=LobsterXAuthentication(api_key=api_key),
        on_error=on_auth_error,
    )

    @app.post(
        "/files",
        dependencies=[
            Depends(RateLimiter(times=file_downloads_per_minute, seconds=60))
        ],
    )
    async def download_file(
        file: UploadFile = File(...),
    ) -> UploadFileResponse:
        file_name = _get_file_name(file)
        file_content = await file.read()
        path = os.path.join(DATA_DIR, file_name)
        await _download_file_to_agentfs(path, file_content)
        return UploadFileResponse(new_file_path=path)

    @app.post(
        "/tasks",
        dependencies=[Depends(RateLimiter(times=tasks_per_minute, seconds=60))],
    )
    async def create_task(request: TaskRequest) -> TaskResponse:
        task_manager = get_task_manager()
        task = asyncio.create_task(handle_prompt(request.prompt))
        task_id = await task_manager.add_task(task)
        return TaskResponse(task_id=task_id)

    @app.delete(
        "/tasks/{task_id}",
        dependencies=[Depends(RateLimiter(times=delete_tasks_per_minute, seconds=60))],
    )
    async def cancel_task(task_id: str) -> JSONResponse:
        task_manager = get_task_manager()
        await task_manager.cancel_task(task_id)
        return JSONResponse(status_code=204, content={})

    @app.get(
        "/tasks/{task_id}",
        dependencies=[Depends(RateLimiter(times=poll_tasks_per_minute, seconds=60))],
    )
    async def get_task(task_id: str) -> GetTaskResponse:
        task_manager = get_task_manager()
        task = await task_manager.check_task(task_id)
        if task is None:
            raise HTTPException(
                status_code=404, detail=f"Task {task_id} does not exist"
            )
        return GetTaskResponse.from_dataclass(task)

    return app
