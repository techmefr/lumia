import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

from arq.connections import ArqRedis, RedisSettings, create_pool

from api.technical.logging.correlation import (
    reset_correlation_id,
    sanitize_correlation_id,
    set_correlation_id,
)
from api.technical.logging.setup import configure_logging
from config.redis import get_redis_config
from worker.domain.pipeline.enrich_article import enrich_article

JOB_EVENT = "job"
_CORRELATION_TOKEN_KEY = "correlation_token"

logger = logging.getLogger("lumia.job")


async def configure_worker_logging(_ctx: dict[str, Any]) -> None:
    configure_logging()


async def bind_job_correlation_id(ctx: dict[str, Any]) -> None:
    """Uses the arq job id as the correlation id so every line a job emits carries it."""
    ctx[_CORRELATION_TOKEN_KEY] = set_correlation_id(
        sanitize_correlation_id(str(ctx.get("job_id") or ""))
    )
    logger.info("job started", extra={"event": JOB_EVENT, "job_try": ctx.get("job_try")})


async def release_job_correlation_id(ctx: dict[str, Any]) -> None:
    logger.info("job finished", extra={"event": JOB_EVENT, "job_try": ctx.get("job_try")})
    token = ctx.pop(_CORRELATION_TOKEN_KEY, None)
    if token is not None:
        reset_correlation_id(token)


class WorkerSettings:
    functions: ClassVar[list[Callable[..., Awaitable[Any]]]] = [enrich_article]
    redis_settings = RedisSettings.from_dsn(get_redis_config().redis_url)
    max_tries: ClassVar[int] = 3
    on_startup = configure_worker_logging
    on_job_start = bind_job_correlation_id
    on_job_end = release_job_correlation_id


_pool: ArqRedis | None = None
_pool_lock = asyncio.Lock()


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await create_pool(RedisSettings.from_dsn(get_redis_config().redis_url))
    return _pool
