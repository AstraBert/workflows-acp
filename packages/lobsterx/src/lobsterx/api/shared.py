import functools
import re


@functools.lru_cache(maxsize=1)
def get_api_key_pattern() -> re.Pattern:
    return re.compile(r"[a-zA-Z0-9_-]{32,}")


@functools.lru_cache(maxsize=1)
def get_auth_header_pattern() -> re.Pattern:
    return re.compile(r"Bearer\s([a-zA-Z0-9_-]{32,})")


def validate_api_key(api_key: str) -> bool:
    pattern = get_api_key_pattern()
    return pattern.match(api_key) is not None
