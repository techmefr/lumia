from datetime import timedelta

from fastapi import HTTPException, Request, status

from api.technical.rate_limit.limiter import (
    RateLimit,
    RateLimiter,
    RateLimitExceededError,
)
from config.rate_limit import get_rate_limit_config


def client_address(request: Request) -> str:
    """The caller's address, read through the trusted proxies the deployment puts in front.

    Each trusted proxy appends the peer it saw to `X-Forwarded-For`, so the entry that many places
    from the right is the last one vouched for — everything to its left was supplied by the caller
    and can say anything.
    """
    config = get_rate_limit_config()
    if config.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            entries = [entry.strip() for entry in forwarded.split(",")]
            return entries[max(len(entries) - config.trusted_proxy_count, 0)]
    return request.client.host if request.client else "unknown"


async def enforce(
    limiter: RateLimiter,
    *,
    scope: str,
    identifiers: dict[str, str],
    max_attempts: int,
    window: timedelta,
) -> None:
    """Counts one attempt per identifier, answering 429 once any of them is over its allowance.

    Two identifiers rather than one: by address alone, an attacker on many addresses walks past the
    limit; by account alone, they lock a reader out of their own account by burning the allowance.
    """
    limit = RateLimit(max_attempts=max_attempts, window=window)
    for kind, value in identifiers.items():
        try:
            await limiter.hit(f"{scope}:{kind}:{value}", limit)
        except RateLimitExceededError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="too many attempts, try again later",
                headers={"Retry-After": str(exc.retry_after_seconds)},
            ) from exc
