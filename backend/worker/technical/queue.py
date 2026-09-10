import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

from arq import cron
from arq.connections import ArqRedis, RedisSettings, create_pool
from arq.cron import CronJob

from config.redis import get_redis_config
from worker.domain.maintenance.purge_tokens import purge_expired_tokens
from worker.domain.maintenance.reconcile_articles import reconcile_recent_articles
from worker.domain.pipeline.enrich_article import enrich_article


class WorkerSettings:
    functions: ClassVar[list[Callable[..., Awaitable[Any]]]] = [enrich_article]
    # Reconciliation on the hour, because a webhook lost at 14:02 should not wait for the night;
    # the purge in the small hours, where a long-running delete disturbs nobody.
    cron_jobs: ClassVar[list[CronJob]] = [
        cron(reconcile_recent_articles, minute=0),
        cron(purge_expired_tokens, hour=3, minute=30),
    ]
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
