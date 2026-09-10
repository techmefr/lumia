from functools import lru_cache

from pydantic_settings import BaseSettings


class RateLimitConfig(BaseSettings):
    """Allowances on the authentication routes, per window and per identifier.

    Sized to be invisible to a reader who mistypes a password and decisive against a script: a
    handful of tries a quarter of an hour, not one a second.
    """

    login_max_attempts: int = 10
    login_window_minutes: int = 15
    magic_link_max_attempts: int = 3
    magic_link_window_minutes: int = 15
    token_max_attempts: int = 30
    token_window_minutes: int = 15
    # The shipped nginx sets X-Forwarded-For; a deployment that exposes the API directly must turn
    # this off, or a caller can pick their own address by sending the header themselves.
    trust_proxy_headers: bool = True


@lru_cache
def get_rate_limit_config() -> RateLimitConfig:
    return RateLimitConfig()
