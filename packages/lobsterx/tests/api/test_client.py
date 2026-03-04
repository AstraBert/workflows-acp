from secrets import token_urlsafe
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from lobsterx.api.client import LobsterXClient
from lobsterx.api.shared import GetTaskResponse
from src.lobsterx.api.task_manager import StatusEnum


class MockResponse:
    def __init__(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return GetTaskResponse(
            status=StatusEnum.PENDING.value,  # type: ignore
            output=None,
            error=None,
        ).model_dump()

    def raise_for_status(self) -> None:
        pass


async def get_pending(*args, **kwargs) -> MockResponse:
    return MockResponse()


@pytest.mark.asyncio
async def test_client_poll_for_task_success() -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = GetTaskResponse(
        status=StatusEnum.SUCCESS.value,  # type: ignore
        output=("hello", "world"),
        error=None,
    ).model_dump()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "lobsterx.api.client.AsyncClient", return_value=mock_async_client
    ) as mock_cls:
        client = LobsterXClient(
            api_key=token_urlsafe(48), host="0.0.0.0", port=8000, protocol="http"
        )
        result = await client.poll_for_task("1234")
        assert result is not None
        assert result.error is None
        assert result.status.value == "success"
        assert result.output == ("hello", "world")
        mock_cls.assert_called_once_with(
            base_url=client.base_url,
            headers={"Authorization": f"Bearer {client.api_key}"},
            timeout=600,
        )
        mock_client.get.assert_called_once_with("/tasks/1234")


@pytest.mark.asyncio
async def test_client_poll_tasks_fails() -> None:
    mock_client = AsyncMock()
    mock_client.get.side_effect = get_pending

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "lobsterx.api.client.AsyncClient", return_value=mock_async_client
    ) as mock_cls:
        client = LobsterXClient(
            api_key=token_urlsafe(48), host="0.0.0.0", port=8000, protocol="http"
        )
        result = await client.poll_for_task(
            "1234", max_attempts=2, polling_interval=0.01
        )
        assert result is None
        mock_cls.assert_called_once_with(
            base_url=client.base_url,
            headers={"Authorization": f"Bearer {client.api_key}"},
            timeout=600,
        )
        mock_client.get.assert_has_calls([call("/tasks/1234"), call("/tasks/1234")])
