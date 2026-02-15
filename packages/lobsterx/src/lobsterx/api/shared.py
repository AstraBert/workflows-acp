import functools
import json
import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class LobsterXApiConfig:
    allow_origins: list[str]
    file_downloads_per_minute: int | None = None
    create_tasks_per_minute: int | None = None
    delete_tasks_per_minute: int | None = None
    poll_tasks_per_minute: int | None = None
    server_api_key: str | None = None

    @classmethod
    def load_from_config(cls, config_file: str) -> "LobsterXApiConfig":
        with open(config_file, "r") as f:
            config = json.load(f)
        return cls(**config)


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
    load_dotenv()
    return os.getenv("LOBSTERX_SERVER_KEY")
