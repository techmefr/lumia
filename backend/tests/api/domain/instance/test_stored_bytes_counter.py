from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import Instance, User
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as db_session:
        yield db_session


async def _user(session: AsyncSession) -> User:
    instance = await session.scalar(select(Instance))
    if instance is None:
        instance = Instance(max_accounts=10, disk_quota_mb=1000)
        session.add(instance)
        await session.flush()
    user = User(instance_id=instance.id, email=f"{uuid4()}@example.com", username="member")
    session.add(user)
    await session.flush()
    return user


async def _feed(session: AsyncSession, user: User) -> Feed:
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MANUAL,
        external_feed_id=str(uuid4()),
        title="feed",
        url="",
    )
    session.add(feed)
    await session.flush()
    return feed


def _article(feed: Feed, content: str, summary: str | None = None) -> Article:
    entry = str(uuid4())
    return Article(
        feed_id=feed.id,
        external_entry_id=entry,
        title="title",
        url=f"https://example.com/{entry}",
        content=content,
        summary=summary,
        published_at=datetime(2026, 9, 1, tzinfo=UTC),
    )


async def _stored_bytes(session: AsyncSession, user: User) -> int:
    value = await session.scalar(select(User.stored_bytes).where(User.id == user.id))
    assert value is not None
    return value


async def test_inserting_an_article_adds_its_content_and_summary(session: AsyncSession) -> None:
    user = await _user(session)
    feed = await _feed(session, user)

    session.add(_article(feed, "abcd", "xy"))
    await session.commit()

    assert await _stored_bytes(session, user) == 6


async def test_an_article_without_a_summary_counts_its_content_only(
    session: AsyncSession,
) -> None:
    user = await _user(session)
    feed = await _feed(session, user)

    session.add(_article(feed, "abcd"))
    await session.commit()

    assert await _stored_bytes(session, user) == 4


async def test_the_counter_measures_bytes_rather_than_characters(session: AsyncSession) -> None:
    user = await _user(session)
    feed = await _feed(session, user)

    session.add(_article(feed, "é"))
    await session.commit()

    assert await _stored_bytes(session, user) == 2


async def test_deleting_an_article_gives_its_bytes_back(session: AsyncSession) -> None:
    user = await _user(session)
    feed = await _feed(session, user)
    kept = _article(feed, "aa")
    removed = _article(feed, "bbbb", "cc")
    session.add_all([kept, removed])
    await session.commit()

    await session.delete(removed)
    await session.commit()

    assert await _stored_bytes(session, user) == 2


async def test_rewriting_the_content_swaps_the_old_size_for_the_new(
    session: AsyncSession,
) -> None:
    user = await _user(session)
    feed = await _feed(session, user)
    article = _article(feed, "abcd", "xy")
    session.add(article)
    await session.commit()

    article.content = "a"
    await session.commit()

    assert await _stored_bytes(session, user) == 3


async def test_rewriting_the_summary_swaps_the_old_size_for_the_new(
    session: AsyncSession,
) -> None:
    user = await _user(session)
    feed = await _feed(session, user)
    article = _article(feed, "abcd", "xy")
    session.add(article)
    await session.commit()

    article.summary = None
    await session.commit()
    assert await _stored_bytes(session, user) == 4

    article.summary = "xyzxyz"
    await session.commit()
    assert await _stored_bytes(session, user) == 10


async def test_moving_an_article_to_another_account_moves_its_bytes(
    session: AsyncSession,
) -> None:
    giver = await _user(session)
    receiver = await _user(session)
    source = await _feed(session, giver)
    target = await _feed(session, receiver)
    article = _article(source, "abcd", "xy")
    session.add(article)
    await session.commit()

    article.feed_id = target.id
    await session.commit()

    assert await _stored_bytes(session, giver) == 0
    assert await _stored_bytes(session, receiver) == 6


async def test_an_update_of_another_column_leaves_the_counter_alone(
    session: AsyncSession,
) -> None:
    user = await _user(session)
    feed = await _feed(session, user)
    article = _article(feed, "abcd")
    session.add(article)
    await session.commit()

    article.title = "another title"
    await session.commit()

    assert await _stored_bytes(session, user) == 4
