from datetime import timedelta
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from api.technical.rate_limit.limiter import (
    RateLimit,
    RateLimitExceededError,
    RedisRateLimiter,
    get_rate_limiter,
)
from config.redis import get_redis_config

LIMIT = RateLimit(max_attempts=3, window=timedelta(minutes=15))


@pytest.fixture
def limiter() -> RedisRateLimiter:
    """Namespaced per test, so runs never inherit a count from an earlier one."""
    return RedisRateLimiter(get_redis_config().redis_url, namespace=f"test:{uuid4()}")


async def test_the_attempts_within_the_allowance_go_through(limiter: RedisRateLimiter) -> None:
    for _ in range(LIMIT.max_attempts):
        await limiter.hit("login:ip:203.0.113.1", LIMIT)


async def test_the_attempt_past_the_allowance_is_refused(limiter: RedisRateLimiter) -> None:
    for _ in range(LIMIT.max_attempts):
        await limiter.hit("login:ip:203.0.113.1", LIMIT)

    with pytest.raises(RateLimitExceededError):
        await limiter.hit("login:ip:203.0.113.1", LIMIT)


async def test_two_keys_have_their_own_allowance(limiter: RedisRateLimiter) -> None:
    for _ in range(LIMIT.max_attempts):
        await limiter.hit("login:ip:203.0.113.1", LIMIT)

    await limiter.hit("login:ip:203.0.113.2", LIMIT)


async def test_the_refusal_says_when_to_come_back(limiter: RedisRateLimiter) -> None:
    for _ in range(LIMIT.max_attempts):
        await limiter.hit("login:ip:203.0.113.1", LIMIT)

    with pytest.raises(RateLimitExceededError) as raised:
        await limiter.hit("login:ip:203.0.113.1", LIMIT)

    assert 0 < raised.value.retry_after_seconds <= LIMIT.window.total_seconds()


async def test_the_counter_expires_with_the_window(limiter: RedisRateLimiter) -> None:
    """Otherwise a first mistyped password would count against a reader forever."""
    await limiter.hit("login:ip:203.0.113.1", LIMIT)

    client: Redis = Redis.from_url(get_redis_config().redis_url)
    try:
        keys = [key.decode() async for key in client.scan_iter(match=f"{limiter.namespace}:*")]
        ttl = await client.ttl(keys[0])
    finally:
        await client.aclose()

    assert 0 < ttl <= LIMIT.window.total_seconds()


def test_the_default_limiter_is_wired_to_the_configured_redis() -> None:
    assert isinstance(get_rate_limiter(), RedisRateLimiter)
