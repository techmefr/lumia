import importlib.util
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Connection, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import MANUAL_FEED_INDEX, Feed, SourceType
from api.domain.user.models import Instance, User
from config.database import get_engine

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "e1b7d4c92a60_one_manual_feed_per_user.py"
)


def _load_merge() -> Callable[[Connection], None]:
    spec = importlib.util.spec_from_file_location("manual_feed_migration", _MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    merge: Callable[[Connection], None] = module._merge_duplicate_manual_feeds
    return merge


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as db_session:
        yield db_session


async def _user(session: AsyncSession, email: str) -> User:
    instance = await session.scalar(select(Instance))
    if instance is None:
        instance = Instance(max_accounts=10, disk_quota_mb=1000)
        session.add(instance)
        await session.flush()
    user = User(instance_id=instance.id, email=email, username=email.split("@")[0])
    session.add(user)
    await session.flush()
    return user


def _feed(user: User, source_type: SourceType, external: str, minute: int) -> Feed:
    return Feed(
        user_id=user.id,
        source_type=source_type,
        external_feed_id=external,
        title=external,
        url="",
        created_at=datetime(2026, 10, 1, 10, minute, tzinfo=UTC),
    )


def _article(feed: Feed, entry: str) -> Article:
    return Article(
        feed_id=feed.id,
        external_entry_id=entry,
        title=entry,
        url=f"https://example.com/{entry}",
        content="c",
        published_at=datetime(2026, 10, 1, tzinfo=UTC),
    )


async def test_the_index_refuses_a_second_manual_feed(session: AsyncSession) -> None:
    user = await _user(session, "a@example.com")
    session.add(_feed(user, SourceType.MANUAL, "manual", 0))
    await session.commit()
    session.add(_feed(user, SourceType.MANUAL, "manual", 1))

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_duplicates_are_merged_into_the_oldest_without_losing_articles(
    session: AsyncSession,
) -> None:
    user = await _user(session, "a@example.com")
    other = await _user(session, "b@example.com")
    await session.execute(text(f"DROP INDEX {MANUAL_FEED_INDEX}"))
    await session.execute(text("ALTER TABLE feeds DROP CONSTRAINT uq_feeds_user_source_external"))
    oldest = _feed(user, SourceType.MANUAL, "manual", 0)
    newer = _feed(user, SourceType.MANUAL, "manual", 5)
    miniflux = _feed(user, SourceType.MINIFLUX, "1", 6)
    other_manual = _feed(other, SourceType.MANUAL, "manual", 7)
    session.add_all([oldest, newer, miniflux, other_manual])
    await session.flush()
    session.add_all([_article(oldest, "a"), _article(newer, "b"), _article(other_manual, "c")])
    await session.commit()

    async with get_engine().begin() as connection:
        await connection.run_sync(_load_merge())

    session.expire_all()
    feeds = {feed.id for feed in await session.scalars(select(Feed))}
    assert feeds == {oldest.id, miniflux.id, other_manual.id}
    homes = {
        article.external_entry_id: article.feed_id
        for article in await session.scalars(select(Article))
    }
    assert homes == {"a": oldest.id, "b": oldest.id, "c": other_manual.id}
