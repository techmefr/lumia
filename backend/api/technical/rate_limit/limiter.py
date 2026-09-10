from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from redis.asyncio import Redis

from config.redis import get_redis_config


@dataclass(frozen=True)
class RateLimit:
    max_attempts: int
    window: timedelta


class RateLimitExceededError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(f"rate limit exceeded, retry in {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds


class RateLimiter(Protocol):
    async def hit(self, key: str, limit: RateLimit) -> None:
        """Counts one attempt against `key`, raising once the window's allowance is spent."""


class RedisRateLimiter:
    """A fixed-window counter in Redis.

    Fixed rather than sliding on purpose: two windows can let through up to twice the allowance at
    a boundary, which is irrelevant at these thresholds and costs one INCR instead of a sorted set
    per attempt.
    """

    def __init__(self, redis_url: str, *, namespace: str = "ratelimit") -> None:
        self._redis_url = redis_url
        self.namespace = namespace

    async def hit(self, key: str, limit: RateLimit) -> None:
        seconds = int(limit.window.total_seconds())
        # A short-lived connection per attempt: the shared arq pool belongs to the worker's event
        # loop, and borrowing it here would tie a login to a loop that may already be closed.
        client: Redis = Redis.from_url(self._redis_url)
        try:
            namespaced = f"{self.namespace}:{key}"
            attempts = await client.incr(namespaced)
            if attempts == 1:
                await client.expire(namespaced, seconds)
            if attempts > limit.max_attempts:
                ttl = await client.ttl(namespaced)
                raise RateLimitExceededError(ttl if ttl > 0 else seconds)
        finally:
            await client.aclose()


def get_rate_limiter() -> RateLimiter:
    return RedisRateLimiter(get_redis_config().redis_url)
