from collections import Counter
from collections.abc import Iterator

import pytest

from api.main import app
from api.technical.rate_limit.limiter import RateLimit, RateLimitExceededError, get_rate_limiter


class InMemoryRateLimiter:
    """The same counting contract as the Redis one, without the shared state between tests."""

    def __init__(self) -> None:
        self.attempts: Counter[str] = Counter()

    async def hit(self, key: str, limit: RateLimit) -> None:
        self.attempts[key] += 1
        if self.attempts[key] > limit.max_attempts:
            raise RateLimitExceededError(int(limit.window.total_seconds()))


@pytest.fixture(autouse=True)
def rate_limiter() -> Iterator[InMemoryRateLimiter]:
    """Every API test gets its own allowance, so one suite cannot spend another's."""
    limiter = InMemoryRateLimiter()
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    yield limiter
    app.dependency_overrides.pop(get_rate_limiter, None)
