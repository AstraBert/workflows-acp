from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    BaseUser,
)
from starlette.requests import HTTPConnection
from starlette.responses import PlainTextResponse, Response

from .shared import get_auth_header_pattern

DEFAULT_DISPLAY_NAME = "lobsterx"
DEFAULT_IDENTITY = "user"


class LobsterXUser(BaseUser):
    def __init__(self, authenticated: bool) -> None:
        self._authenticated = authenticated

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    @property
    def identity(self) -> str:
        return DEFAULT_IDENTITY

    @property
    def display_name(self) -> str:
        return DEFAULT_DISPLAY_NAME


class LobsterXAuthentication(AuthenticationBackend):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def authenticate(
        self, conn: HTTPConnection
    ) -> tuple[AuthCredentials, BaseUser] | None:
        auth_header = conn.headers.get("Authorization", None)
        if auth_header is None:
            raise AuthenticationError("No authorization header in request")
        matches = get_auth_header_pattern().findall(auth_header)
        try:
            assert len(matches) == 1, "Should only provide one bearer token"
        except AssertionError as e:
            raise AuthenticationError("Should only provide one bearer token") from e
        api_key = matches[0]
        if api_key == self.api_key:
            return AuthCredentials(scopes=["http"]), LobsterXUser(authenticated=True)
        raise AuthenticationError("API key not authorized")


def on_auth_error(conn: HTTPConnection, exc: AuthenticationError) -> Response:
    return PlainTextResponse(str(exc), status_code=401)
