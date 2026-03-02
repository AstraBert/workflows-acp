import json
from pathlib import Path
from secrets import token_urlsafe

import pytest

from lobsterx.api.api import validate_api_key
from lobsterx.api.shared import GetTaskResponse, LobsterXApiConfig
from lobsterx.api.task_manager import StatusEnum, TaskRepr


def test_lobsterx_api_config_correct_config() -> None:
    conf = LobsterXApiConfig.load_from_config("config.api.json")
    assert conf.allow_origins == []
    assert conf.create_tasks_per_minute == 60
    assert conf.delete_tasks_per_minute == 60
    assert conf.poll_tasks_per_minute == 300
    assert conf.file_downloads_per_minute == 300
    assert conf.port == 9000
    assert conf.host == "0.0.0.0"
    assert conf.protocol == "http"
    assert conf.server_api_key is None


def test_lobsterx_api_config_wrong(tmp_path: Path) -> None:
    with open("config.api.json") as f:
        data = json.load(f)
        assert isinstance(data, dict)
        data.pop("create_tasks_per_minute")
        data["create_task_per_minute"] = 50
    new_cfg = tmp_path / "config.json"
    new_cfg.write_text(json.dumps(data))
    with pytest.raises(TypeError):
        LobsterXApiConfig.load_from_config(str(new_cfg))


def test_lobsterx_api_config_to_args() -> None:
    conf = LobsterXApiConfig.load_from_config("config.api.json")
    args = conf.to_args()
    assert "allow_origins" in args
    assert "create_tasks_per_minute" in args
    assert "delete_tasks_per_minute" in args
    assert "poll_tasks_per_minute" in args
    assert "file_downloads_per_minute" in args
    assert "server_api_key" in args
    assert "host" not in args
    assert "port" not in args
    assert "protocol" not in args


def test_get_task_response_from_task_repr() -> None:
    repr = TaskRepr(status=StatusEnum.SUCCESS, output=("hello", "world"), error=None)
    response = GetTaskResponse.from_dataclass(repr)
    assert response.status.value == "success"
    assert response.output == ("hello", "world")
    assert response.error is None


def test_validate_api_key_correct() -> None:
    valid_api_key = token_urlsafe(32)  # always valid key
    assert validate_api_key(valid_api_key)


def test_validate_api_key_too_short() -> None:
    invalid_api_key = token_urlsafe(16)  # always valid key, but less than 32
    assert not validate_api_key(invalid_api_key)


def test_validate_api_key_invalid() -> None:
    invalid_api_key = "This?is-alitt5le=someYvdjwhuiabaf74q93$nfeooN)"  # len > 32, but does not match regex
    assert not validate_api_key(invalid_api_key)
