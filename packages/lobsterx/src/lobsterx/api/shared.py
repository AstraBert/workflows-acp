import functools
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel

from .task_manager import StatusEnum, TaskRepr


@dataclass
class LobsterXApiConfig:
    allow_origins: list[str]
    file_downloads_per_minute: int | None = None
    create_tasks_per_minute: int | None = None
    delete_tasks_per_minute: int | None = None
    poll_tasks_per_minute: int | None = None
    server_api_key: str | None = None
    host: str | None = None
    port: int | None = None
    protocol: Literal["http", "https"] = "http"

    @classmethod
    def load_from_config(cls, config_file: str) -> "LobsterXApiConfig":
        with open(config_file, "r") as f:
            config = json.load(f)
        return cls(**config)

    def to_args(self) -> dict[str, Any]:
        return {
            "allow_origins": self.allow_origins,
            "file_downloads_per_minute": self.file_downloads_per_minute,
            "create_tasks_per_minute": self.create_tasks_per_minute,
            "delete_tasks_per_minute": self.delete_tasks_per_minute,
            "poll_tasks_per_minute": self.poll_tasks_per_minute,
            "server_api_key": self.server_api_key,
        }


@functools.lru_cache(maxsize=1)
def get_api_key_pattern() -> re.Pattern:
    return re.compile(r"[a-zA-Z0-9_-]{32,}")


@functools.lru_cache(maxsize=1)
def get_auth_header_pattern() -> re.Pattern:
    return re.compile(r"Bearer\s([a-zA-Z0-9_-]{32,})")


def validate_api_key(api_key: str) -> bool:
    pattern = get_api_key_pattern()
    return pattern.match(api_key) is not None


@functools.lru_cache(maxsize=1)
def get_server_key_from_env() -> str | None:
    load_dotenv(".env")
    return os.getenv("LOBSTERX_SERVER_KEY")


class TaskRequest(BaseModel):
    prompt: str


class TaskResponse(BaseModel):
    task_id: str


class GetTaskResponse(BaseModel):
    status: StatusEnum
    output: tuple[str, str] | None = None
    error: str | None = None

    @classmethod
    def from_dataclass(cls, task_repr: TaskRepr) -> "GetTaskResponse":
        return cls(
            status=task_repr.status, output=task_repr.output, error=task_repr.error
        )


class UploadFileResponse(BaseModel):
    new_file_path: str
