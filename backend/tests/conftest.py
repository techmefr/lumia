import asyncio
import os
from collections.abc import AsyncIterator, Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from tests.database_naming import maintenance_url, run_database_url

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://lumia:lumia@localhost:55432/lumia_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-at-least-32-bytes-long")
os.environ.setdefault("SECRET_ENCRYPTION_KEY", "LcYOJkf45vBbcjn7M8_S69E2pQfd_Qv8GNOW2_HkJpk=")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_USERNAME", "test")
os.environ.setdefault("SMTP_PASSWORD", "test")
os.environ.setdefault("SMTP_FROM_ADDRESS", "lumia@example.com")
os.environ.setdefault("MINIFLUX_BASE_URL", "http://miniflux.test")
os.environ.setdefault("MINIFLUX_USERNAME", "admin")
os.environ.setdefault("MINIFLUX_PASSWORD", "test-miniflux-password")
os.environ.setdefault("MINIFLUX_WEBHOOK_SECRET", "test-miniflux-webhook-secret")
os.environ.setdefault("DEEPL_API_KEY", "test-deepl-key")

# The run takes a database of its own before anything reads DATABASE_URL, so two pytest runs
# started side by side stop wiping each other's schema mid-test.
_CONFIGURED_DATABASE_URL = os.environ["DATABASE_URL"]
os.environ["DATABASE_URL"] = run_database_url(
    _CONFIGURED_DATABASE_URL,
    worker=os.environ.get("PYTEST_XDIST_WORKER"),
    pid=os.getpid(),
)

from api.domain.article import models as _article_models  # noqa: F401
from api.domain.feed import models as _feed_models  # noqa: F401
from api.domain.instance import models as _instance_models  # noqa: F401
from api.domain.playlist import models as _playlist_models  # noqa: F401
from api.domain.recommendation import models as _recommendation_models  # noqa: F401
from api.domain.user import models as _user_models  # noqa: F401
from api.technical.orm import Base
from config.database import get_engine


async def _execute_on_the_server(statement: str) -> None:
    """Creating a database runs outside any database of ours, and outside a transaction."""
    engine = create_async_engine(
        maintenance_url(_CONFIGURED_DATABASE_URL), isolation_level="AUTOCOMMIT"
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


def _on_the_server(statement: str) -> None:
    asyncio.run(_execute_on_the_server(statement))


@pytest.fixture(scope="session")
def run_database() -> Iterator[None]:
    name = make_url(os.environ["DATABASE_URL"]).database
    # A previous run killed before its teardown would otherwise leave its tables behind.
    _on_the_server(f'drop database if exists "{name}"')
    _on_the_server(f'create database "{name}"')
    yield
    _on_the_server(f'drop database if exists "{name}"')


@pytest.fixture
async def db_schema(run_database: None) -> AsyncIterator[None]:
    get_engine.cache_clear()
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    get_engine.cache_clear()
