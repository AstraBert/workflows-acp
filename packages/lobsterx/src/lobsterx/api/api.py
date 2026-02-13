import mimetypes
import os

from fastapi import FastAPI
from fastapi.datastructures import UploadFile
from fastapi.param_functions import Depends, File
from fastapi_throttle import RateLimiter
from pydantic import BaseModel
from random_name import generate_name
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware

from ..constants import DATA_DIR
from ..utils import _download_file_to_agentfs
from .auth import LobsterXAuthentication, on_auth_error
from .shared import validate_api_key

DEFAULT_FILE_DOWNLOADS_PER_MINUTE = 300
DEFAULT_TASKS_PER_MINUTE = 60


class TaskRequest(BaseModel):
    prompt: str


class TaskResponse(BaseModel):
    final_respose: str
    report: str


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
    tasks_per_minute: int | None,
    api_key: str | None,
) -> FastAPI:
    app = FastAPI()

    file_downloads_per_minute = (
        file_downloads_per_minute or DEFAULT_FILE_DOWNLOADS_PER_MINUTE
    )
    tasks_per_minute = tasks_per_minute or DEFAULT_TASKS_PER_MINUTE
    api_key = api_key or os.getenv("LOBSTERX_SERVER_KEY")
    if api_key is None:
        raise ValueError(
            "API key not provided and `LOBSTERX_SERVER_KEY` not found within the current environment"
        )

    if not validate_api_key(api_key):
        raise ValueError(
            "API key should be an a string of letters, numbers, hyphens and underscores, with a minimum length of 32."
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type"],
    )

    app.add_middleware(
        AuthenticationMiddleware,
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
    ) -> None:
        file_name = _get_file_name(file)
        file_content = await file.read()
        path = os.path.join(DATA_DIR, file_name)
        await _download_file_to_agentfs(path, file_content)

    @app.post(
        "/tasks",
        dependencies=[Depends(RateLimiter(times=tasks_per_minute, seconds=60))],
    )
    async def process_task(request: TaskRequest) -> None:
        pass

    return app
