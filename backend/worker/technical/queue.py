import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

from arq.connections import ArqRedis, RedisSettings, create_pool

from config.redis import get_redis_config


class WorkerSettings:
    functions: ClassVar[list[Callable[..., Awaitable[Any]]]] = []
    redis_settings = RedisSettings.from_dsn(get_redis_config().redis_url)


_pool: ArqRedis | None = None
_pool_lock = asyncio.Lock()


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await create_pool(RedisSettings.from_dsn(get_redis_config().redis_url))
    return _pool
