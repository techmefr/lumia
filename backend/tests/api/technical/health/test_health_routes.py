from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import app
from api.technical.db import get_db_session


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


class _UnreachableDatabase:
    """Stands in for a session whose connection is gone, which is what a probe has to survive."""

    async def execute(self, statement: Any) -> Any:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


async def test_health_answers_without_touching_the_database(client: httpx.AsyncClient) -> None:
    def fail_if_used() -> AsyncSession:
        raise AssertionError("the liveness probe must not open a database session")

    app.dependency_overrides[get_db_session] = fail_if_used

    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_reports_both_services_up(client: httpx.AsyncClient) -> None:
    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"database": "ok", "redis": "ok"}


async def test_ready_answers_503_when_the_database_is_unreachable(
    client: httpx.AsyncClient,
) -> None:
    app.dependency_overrides[get_db_session] = _UnreachableDatabase

    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"database": "down", "redis": "ok"}


async def test_ready_answers_503_when_redis_is_unreachable(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _UnreachableRedis:
        async def ping(self) -> Any:
            raise RedisConnectionError("connection refused")

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(Redis, "from_url", classmethod(lambda cls, url: _UnreachableRedis()))

    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"database": "ok", "redis": "down"}
