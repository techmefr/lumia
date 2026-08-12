from worker.technical.queue import WorkerSettings


def test_worker_settings_has_a_functions_list() -> None:
    assert isinstance(WorkerSettings.functions, list)


def test_worker_settings_redis_settings_matches_env() -> None:
    assert WorkerSettings.redis_settings.host == "localhost"
    assert WorkerSettings.redis_settings.port == 6379
    assert WorkerSettings.redis_settings.database == 1
