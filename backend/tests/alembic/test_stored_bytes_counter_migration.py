import importlib.util
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import UUID, uuid4

import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Connection, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.instance.usage_triggers import LOCK_ARTICLES, LOCK_TIMEOUT
from api.domain.user.models import Instance, User
from config.database import get_engine

_VERSIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"
_RECOMPUTE = _VERSIONS / "e9b3c5a17d42_recompute_stored_bytes_counter.py"
_ORIGINAL = _VERSIONS / "d4e7f0a23b54_keep_stored_bytes_counter.py"


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_upgrade(connection: Connection, path: Path) -> None:
    module = _load(path)
    with Operations.context(MigrationContext.configure(connection)):
        module.upgrade()


def _strip_counter(connection: Connection) -> None:
    connection.execute(text("DROP TRIGGER trg_articles_stored_bytes ON articles"))
    connection.execute(text("ALTER TABLE users DROP COLUMN stored_bytes"))


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as db_session:
        yield db_session


async def _seed(session: AsyncSession) -> tuple[UUID, UUID]:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    users = [
        User(instance_id=instance.id, email=f"{uuid4()}@example.com", username="member")
        for _ in range(2)
    ]
    session.add_all(users)
    await session.flush()
    feed = Feed(
        user_id=users[0].id,
        source_type=SourceType.MANUAL,
        external_feed_id="manual",
        title="feed",
        url="",
    )
    session.add(feed)
    await session.flush()
    for index, (content, summary) in enumerate([("abcd", "xy"), ("é", None)]):
        session.add(
            Article(
                feed_id=feed.id,
                external_entry_id=str(index),
                title="title",
                url=f"https://example.com/{index}",
                content=content,
                summary=summary,
                published_at=datetime(2026, 9, 1, tzinfo=UTC),
            )
        )
    await session.commit()
    return users[0].id, users[1].id


async def _counters(session: AsyncSession) -> dict[UUID, int]:
    session.expire_all()
    rows = (await session.execute(select(User.id, User.stored_bytes))).all()
    return dict(rows)


async def test_the_recompute_migration_repairs_a_drifted_counter(session: AsyncSession) -> None:
    busy, idle = await _seed(session)
    await session.execute(text("UPDATE users SET stored_bytes = 99999"))
    await session.commit()

    async with get_engine().begin() as connection:
        await connection.run_sync(_run_upgrade, _RECOMPUTE)

    counters = await _counters(session)
    assert counters[busy] == 8
    assert counters[idle] == 0


async def test_the_backfill_of_the_original_migration_counts_existing_articles(
    session: AsyncSession,
) -> None:
    busy, idle = await _seed(session)
    async with get_engine().begin() as connection:
        await connection.run_sync(_strip_counter)
        await connection.run_sync(_run_upgrade, _ORIGINAL)

    counters = await _counters(session)
    assert counters[busy] == 8
    assert counters[idle] == 0


async def test_an_article_written_after_the_original_migration_is_counted_by_the_trigger(
    session: AsyncSession,
) -> None:
    busy, _ = await _seed(session)
    async with get_engine().begin() as connection:
        await connection.run_sync(_strip_counter)
        await connection.run_sync(_run_upgrade, _ORIGINAL)

    feed = await session.scalar(select(Feed).where(Feed.user_id == busy))
    assert feed is not None
    session.add(
        Article(
            feed_id=feed.id,
            external_entry_id="later",
            title="title",
            url="https://example.com/later",
            content="zz",
            published_at=datetime(2026, 9, 1, tzinfo=UTC),
        )
    )
    await session.commit()

    assert (await _counters(session))[busy] == 10


async def test_the_lock_keeps_a_concurrent_article_out_while_the_counter_is_rebuilt(
    session: AsyncSession,
) -> None:
    busy, _ = await _seed(session)
    feed = await session.scalar(select(Feed).where(Feed.user_id == busy))
    assert feed is not None

    async with get_engine().connect() as locker:
        transaction = await locker.begin()
        await locker.execute(text(LOCK_TIMEOUT))
        await locker.execute(text(LOCK_ARTICLES))

        async with get_engine().connect() as writer:
            await writer.execute(text("SET lock_timeout = '300ms'"))
            with pytest.raises(DBAPIError):
                await writer.execute(
                    text(
                        "INSERT INTO articles (id, feed_id, external_entry_id, title, url,"
                        " content, published_at, created_at) VALUES (gen_random_uuid(),"
                        " :feed, 'blocked', 't', 'https://example.com/blocked',"
                        " 'c', now(), now())"
                    ),
                    {"feed": feed.id},
                )
        await transaction.rollback()
