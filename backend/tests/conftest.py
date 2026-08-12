import os
from collections.abc import AsyncIterator

import pytest

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://lumia:lumia@localhost:55432/lumia_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-at-least-32-bytes-long")
os.environ.setdefault("SECRET_ENCRYPTION_KEY", "LcYOJkf45vBbcjn7M8_S69E2pQfd_Qv8GNOW2_HkJpk=")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_USERNAME", "test")
os.environ.setdefault("SMTP_PASSWORD", "test")
os.environ.setdefault("SMTP_FROM_ADDRESS", "lumia@example.com")

from api.domain.article import models as _article_models  # noqa: F401
from api.domain.feed import models as _feed_models  # noqa: F401
from api.domain.recommendation import models as _recommendation_models  # noqa: F401
from api.domain.user import models as _user_models  # noqa: F401
from api.technical.orm import Base
from config.database import get_engine


@pytest.fixture
async def db_schema() -> AsyncIterator[None]:
    get_engine.cache_clear()
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    get_engine.cache_clear()
