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
    # Tighter than a password: six digits is a million guesses, and the reader trying them already
    # holds the first factor, so every allowed attempt is one an attacker has bought.
    totp_max_attempts: int = 5
    totp_window_minutes: int = 15
    # Manual refreshes reach past Lumia and make a third-party server fetch a feed, so the ceiling
    # protects the publisher as much as the instance. One feed a few times a quarter of an hour is
    # enough to answer "is it fixed yet?"; the whole account is an order of magnitude dearer,
    # because Miniflux refreshes per account and one reader's click pulls every feed on a shared
    # instance, so it gets a much smaller allowance over a longer window.
    feed_refresh_max_attempts: int = 10
    feed_refresh_window_minutes: int = 15
    feed_refresh_all_max_attempts: int = 3
    feed_refresh_all_window_minutes: int = 60
    # The shipped nginx sets X-Forwarded-For; a deployment that exposes the API directly must turn
    # this off, or a caller can pick their own address by sending the header themselves.
    trust_proxy_headers: bool = True


@lru_cache
def get_rate_limit_config() -> RateLimitConfig:
    return RateLimitConfig()
