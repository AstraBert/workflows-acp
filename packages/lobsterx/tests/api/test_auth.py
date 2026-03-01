from secrets import token_urlsafe

import pytest
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from lobsterx.api.auth import (
    DEFAULT_DISPLAY_NAME,
    DEFAULT_IDENTITY,
    AuthenticationError,
    LobsterXAuthentication,
    LobsterXUser,
    on_auth_error,
)


def mock_request(
    api_key: str, invalid_header: bool = False, no_header: bool = False
) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": Headers({"Authorization": f"Bearer {api_key}"}).raw,
        "query_string": b"",
    }
    if invalid_header:
        scope["headers"] = Headers(
            {"Authorization": f"Bearer {api_key} Bearer {api_key}"}
        ).raw
    elif no_header:
        scope["headers"] = Headers({"Content-Type": "application/json"}).raw
    return Request(scope)


def test_lobsterx_user() -> None:
    user = LobsterXUser(authenticated=False)
    assert not user.is_authenticated
    assert user.display_name == DEFAULT_DISPLAY_NAME
    assert user.identity == DEFAULT_IDENTITY
    user1 = LobsterXUser(authenticated=True)
    assert user1.is_authenticated


@pytest.mark.asyncio
async def test_lobsterx_auth_success() -> None:
    api_key = token_urlsafe(32)
    auth = LobsterXAuthentication(api_key)
    request = mock_request(api_key)
    creds = await auth.authenticate(request)
    assert creds is not None
    assert creds[0].scopes == ["http"]
    assert creds[1].is_authenticated
    assert creds[1].display_name == DEFAULT_DISPLAY_NAME
    assert creds[1].identity == DEFAULT_IDENTITY


@pytest.mark.asyncio
async def test_lobsterx_auth_invalid_key() -> None:
    api_key = token_urlsafe(32)
    other_key = token_urlsafe(48)
    auth = LobsterXAuthentication(api_key)
    request = mock_request(other_key)
    with pytest.raises(AuthenticationError, match="API key not authorized"):
        await auth.authenticate(request)


@pytest.mark.asyncio
async def test_lobsterx_auth_no_header() -> None:
    api_key = token_urlsafe(32)
    auth = LobsterXAuthentication(api_key)
    request = mock_request(api_key, no_header=True)
    with pytest.raises(AuthenticationError, match="No authorization header in request"):
        await auth.authenticate(request)


@pytest.mark.asyncio
async def test_lobsterx_auth_double_header() -> None:
    api_key = token_urlsafe(32)
    auth = LobsterXAuthentication(api_key)
    request = mock_request(api_key, invalid_header=True)
    with pytest.raises(
        AuthenticationError, match="Should only provide one bearer token"
    ):
        await auth.authenticate(request)


def test_lobsterx_auth_on_error() -> None:
    api_key = token_urlsafe(32)
    request = mock_request(api_key, invalid_header=True)
    resp = on_auth_error(request, AuthenticationError("An error occurred"))
    assert isinstance(resp, PlainTextResponse)
    assert resp.status_code == 401
    assert str(resp.body, encoding="utf-8") == "An error occurred"
