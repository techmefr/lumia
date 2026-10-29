import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

from arq import cron
from arq.connections import ArqRedis, RedisSettings, create_pool
from arq.cron import CronJob
from arq.worker import Function

from api.technical.logging.correlation import (
    reset_correlation_id,
    sanitize_correlation_id,
    set_correlation_id,
)
from api.technical.logging.setup import configure_logging
from config.redis import get_redis_config
from worker.domain.digest.send_digests import send_reader_digests
from worker.domain.export.build_playlist_epub import build_playlist_epub
from worker.domain.imports.import_reading_list import import_reading_list
from worker.domain.maintenance.purge_exports import purge_expired_exports
from worker.domain.maintenance.purge_tokens import purge_expired_tokens
from worker.domain.maintenance.purge_webhook_deliveries import purge_old_webhook_deliveries
from worker.domain.maintenance.reconcile_articles import reconcile_recent_articles
from worker.domain.maintenance.refresh_due_feeds import refresh_due_feeds
from worker.domain.maintenance.sync_feed_status import sync_feed_error_status
from worker.domain.pipeline.enrich_article import enrich_article
from worker.domain.webhook.deliver_webhook import deliver_webhook_function

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
    functions: ClassVar[list[Callable[..., Awaitable[Any]] | Function]] = [
        enrich_article,
        import_reading_list,
        build_playlist_epub,
        deliver_webhook_function,
    ]
    # Reconciliation on the hour, because a webhook lost at 14:02 should not wait for the night;
    # the purge in the small hours, where a long-running delete disturbs nobody; the feed status
    # sync every 15 minutes, so a feed going silent surfaces well within the same reading session;
    # the scheduled refresh every 5 minutes, which is the shortest interval a feed can be given and
    # therefore the resolution the whole per-feed schedule is capable of; the digests once an hour,
    # because the hour that matters is each reader's own and the job itself decides who is due.
    cron_jobs: ClassVar[list[CronJob]] = [
        cron(reconcile_recent_articles, minute=0),
        cron(purge_expired_tokens, hour=3, minute=30),
        cron(sync_feed_error_status, minute={0, 15, 30, 45}),
        cron(refresh_due_feeds, minute=set(range(0, 60, 5))),
        cron(send_reader_digests, minute=5),
        cron(purge_expired_exports, hour=4, minute=0),
        cron(purge_old_webhook_deliveries, hour=4, minute=30),
    ]
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
