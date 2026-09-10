import logging
import os
from urllib.parse import urlparse

import pytest

from api.technical.logging.correlation import get_correlation_id
from worker.technical.queue import (
    WorkerSettings,
    bind_job_correlation_id,
    configure_worker_logging,
    release_job_correlation_id,
)


def test_worker_settings_has_a_functions_list() -> None:
    assert isinstance(WorkerSettings.functions, list)


def test_worker_settings_redis_settings_matches_env() -> None:
    """The point is that REDIS_URL is what drives the worker, not a hardcoded host.

    Parsed from the environment rather than asserted against a literal, so the test says the same
    thing whether it runs against a local redis or one reached by its service name.
    """
    url = urlparse(os.environ["REDIS_URL"])
    assert WorkerSettings.redis_settings.host == url.hostname
    assert WorkerSettings.redis_settings.port == (url.port or 6379)
    assert WorkerSettings.redis_settings.database == int(url.path.lstrip("/") or 0)


def test_worker_settings_configures_a_finite_retry_count() -> None:
    assert WorkerSettings.max_tries == 3


async def test_job_hooks_bind_the_job_id_as_the_correlation_id_and_release_it() -> None:
    ctx: dict[str, object] = {"job_id": "job-42", "job_try": 1}

    await bind_job_correlation_id(ctx)
    assert get_correlation_id() == "job-42"

    await release_job_correlation_id(ctx)
    assert get_correlation_id() is None


async def test_job_hooks_mint_a_correlation_id_when_arq_gives_no_job_id() -> None:
    ctx: dict[str, object] = {"job_try": 1}

    await bind_job_correlation_id(ctx)
    bound = get_correlation_id()
    await release_job_correlation_id(ctx)

    assert bound is not None


async def test_job_start_is_logged_under_the_job_correlation_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ctx: dict[str, object] = {"job_id": "job-7", "job_try": 2}
    with caplog.at_level(logging.INFO, logger="lumia.job"):
        await bind_job_correlation_id(ctx)
        await release_job_correlation_id(ctx)

    assert [record.message for record in caplog.records] == ["job started", "job finished"]


def test_worker_settings_wires_the_logging_and_correlation_hooks() -> None:
    assert WorkerSettings.on_startup is configure_worker_logging
    assert WorkerSettings.on_job_start is bind_job_correlation_id
    assert WorkerSettings.on_job_end is release_job_correlation_id


async def test_worker_startup_installs_the_shared_log_handler() -> None:
    root_logger = logging.getLogger()
    handlers = list(root_logger.handlers)
    level = root_logger.level
    try:
        await configure_worker_logging({})
        assert len(root_logger.handlers) == 1
    finally:
        root_logger.handlers = handlers
        root_logger.setLevel(level)
