from tests.database_naming import maintenance_url, run_database_url

BASE = "postgresql+asyncpg://lumia:lumia@localhost:55432/lumia_test"


def test_two_runs_without_xdist_get_two_databases() -> None:
    first = run_database_url(BASE, worker=None, pid=1234)
    second = run_database_url(BASE, worker=None, pid=5678)

    assert first != second
    assert first.endswith("/lumia_test_p1234")
    assert second.endswith("/lumia_test_p5678")


def test_each_xdist_worker_gets_its_own_database() -> None:
    first = run_database_url(BASE, worker="gw0", pid=1234)
    second = run_database_url(BASE, worker="gw1", pid=1234)

    assert first.endswith("/lumia_test_gw0")
    assert second.endswith("/lumia_test_gw1")


def test_the_rest_of_the_connection_is_left_alone() -> None:
    url = run_database_url(BASE, worker=None, pid=1)

    assert url.startswith("postgresql+asyncpg://lumia:lumia@localhost:55432/")


def test_the_maintenance_connection_targets_the_always_present_database() -> None:
    """`create database` cannot run from inside the database it creates."""
    assert maintenance_url(BASE).endswith("/postgres")
