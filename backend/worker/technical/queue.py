import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

from arq.connections import ArqRedis, RedisSettings, create_pool

from config.redis import get_redis_config
from worker.domain.pipeline.enrich_article import enrich_article


class WorkerSettings:
    functions: ClassVar[list[Callable[..., Awaitable[Any]]]] = [enrich_article]
    redis_settings = RedisSettings.from_dsn(get_redis_config().redis_url)
    max_tries: ClassVar[int] = 3


_pool: ArqRedis | None = None
_pool_lock = asyncio.Lock()


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await create_pool(RedisSettings.from_dsn(get_redis_config().redis_url))
    return _pool
