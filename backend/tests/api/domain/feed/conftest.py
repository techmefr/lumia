from collections.abc import Iterator

import pytest

from api.main import app
from tests.fake_arq_pool import FakeArqPool
from worker.technical.queue import get_arq_pool


@pytest.fixture(autouse=True)
def arq_pool() -> Iterator[FakeArqPool]:
    """Adding a feed queues a reconciliation; the real pool is bound to the first test's loop."""
    pool = FakeArqPool()
    app.dependency_overrides[get_arq_pool] = lambda: pool
    yield pool
    app.dependency_overrides.pop(get_arq_pool, None)
