from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.import_progress import read_progress, start_progress
from api.domain.article.models import Article
from api.domain.user.models import Instance, User
from config.database import get_engine
from tests.fake_arq_pool import FakeArqPool
from worker.domain.imports.import_reading_list import import_reading_list
from worker.technical.content_extraction import ExtractedPage, PageFetchError


class _Extractor:
    async def fetch(self, url: str) -> ExtractedPage:
        if "dead" in url:
            raise PageFetchError("gone")
        return ExtractedPage(title=url, content="<p>body</p>")


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with factory() as db_session:
        yield db_session


async def _user(session: AsyncSession) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(instance_id=instance.id, email=f"{uuid4()}@example.com", username="reader")
    session.add(user)
    await session.commit()
    return user


async def test_each_link_is_saved_and_the_dead_ones_are_counted_not_fatal(
    session: AsyncSession,
) -> None:
    user = await _user(session)
    pool = FakeArqPool()
    await start_progress(pool, "imp", user.id, 3)

    saved = await import_reading_list(
        {"redis": pool, "page_extractor": _Extractor()},
        str(user.id),
        "imp",
        ["https://example.com/a", "https://dead.example.com/b", "https://example.com/c"],
    )

    progress = await read_progress(pool, "imp", user.id)
    assert saved == 2
    assert progress == {"total": 3, "saved": 2, "failed": 1, "finished": True}
    assert await session.scalar(select(func.count()).select_from(Article)) == 2


async def test_a_retried_job_does_not_count_links_twice(session: AsyncSession) -> None:
    user = await _user(session)
    pool = FakeArqPool()
    await start_progress(pool, "imp", user.id, 1)
    ctx = {"redis": pool, "page_extractor": _Extractor()}

    await import_reading_list(ctx, str(user.id), "imp", ["https://example.com/a"])
    await import_reading_list(ctx, str(user.id), "imp", ["https://example.com/a"])

    progress = await read_progress(pool, "imp", user.id)
    assert progress["saved"] == 1
    assert await session.scalar(select(func.count()).select_from(Article)) == 1


async def test_a_user_who_no_longer_exists_has_every_link_counted_failed(
    session: AsyncSession,
) -> None:
    pool = FakeArqPool()
    ghost = uuid4()
    await start_progress(pool, "imp", ghost, 1)

    saved = await import_reading_list(
        {"redis": pool, "page_extractor": _Extractor()},
        str(ghost),
        "imp",
        ["https://example.com/a"],
    )

    assert saved == 0
    assert (await read_progress(pool, "imp", ghost))["failed"] == 1
