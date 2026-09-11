from arq.connections import ArqRedis

from worker.technical.queue import WorkerSettings, get_arq_pool


async def test_get_arq_pool_returns_the_same_pool_on_repeated_calls() -> None:
    first = await get_arq_pool()
    second = await get_arq_pool()
    assert first is second
    assert isinstance(first, ArqRedis)


def test_the_worker_schedules_the_reconciliation_the_purge_and_the_feed_status_sync() -> None:
    """A cron job written but never registered looks exactly like one that works."""
    scheduled = {job.name for job in WorkerSettings.cron_jobs}
    assert scheduled == {
        "cron:reconcile_recent_articles",
        "cron:purge_expired_tokens",
        "cron:sync_feed_error_status",
    }


def test_the_reconciliation_runs_every_hour_and_the_purge_once_a_night() -> None:
    by_name = {job.name: job for job in WorkerSettings.cron_jobs}
    assert by_name["cron:reconcile_recent_articles"].hour is None
    assert by_name["cron:purge_expired_tokens"].hour == 3
