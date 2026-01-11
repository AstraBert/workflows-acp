import asyncio
import logging
from functools import wraps
from typing import TypeVar, Callable, Awaitable, Literal, cast
from pydantic import BaseModel

F = TypeVar("F", bound=Callable[..., Awaitable[BaseModel | None]])


def retry(
    max_retries: int = 3,
    retry_interval: float = 1,
    max_retry_interval: float = 10,
    backoff_pattern: Literal["exponential", "linear"] = "linear",
) -> Callable[[F], F]:
    def decorator(f: F) -> F:
        @wraps(f)
        async def wrapper(*args, **kwargs) -> BaseModel | None:
            retries = 0
            exception = None
            while retries < max_retries:
                try:
                    return await f(*args, **kwargs)
                except Exception as e:
                    logging.debug(
                        f"Got exception: {e}. Retrying ({retries}/{max_retries})..."
                    )
                    exception = e
                    if backoff_pattern == "linear":
                        delay = min(max_retry_interval, retry_interval * (retries + 1))
                    else:
                        delay = min(max_retry_interval, retry_interval * (2**retries))
                    retries += 1
                    if retries <= max_retries - 1:
                        await asyncio.sleep(delay)
            if exception is not None and retries == max_retries:
                raise exception
            return None

        return cast(F, wrapper)

    return decorator
