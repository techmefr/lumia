import os
from urllib.parse import urlparse

from worker.technical.queue import WorkerSettings


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
