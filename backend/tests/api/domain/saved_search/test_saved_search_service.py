from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.article.search_filters import SearchFilters
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.bulk_feedback_service import FeedbackAxis, set_feedback_axis
from api.domain.saved_search.saved_search_service import (
    count_unread_matches,
    create_saved_search,
    run_saved_search,
)
from api.domain.user.models import Instance, User
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _reader(session: AsyncSession) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(instance_id=instance.id, email=f"{uuid4()}@example.com", username="reader")
    session.add(user)
    await session.commit()
    return user


async def _feed(session: AsyncSession, user: User) -> Feed:
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id=str(uuid4()),
        title="Le Blog",
        url=f"https://blog.test/{uuid4()}",
    )
    session.add(feed)
    await session.flush()
    return feed


async def _article(session: AsyncSession, feed: Feed, *, title: str) -> Article:
    article = Article(
        feed_id=feed.id,
        external_entry_id=str(uuid4()),
        title=title,
        url=f"https://blog.test/{uuid4()}",
        content="<p>x</p>",
        summary=None,
        published_at=datetime.now(UTC),
    )
    session.add(article)
    await session.commit()
    return article


async def test_an_empty_saved_search_has_no_unread_matches(session: AsyncSession) -> None:
    user = await _reader(session)
    saved_search = await create_saved_search(
        session,
        user.id,
        name="Nothing yet",
        filters=SearchFilters(query="unobtainium"),
        is_alert=False,
    )

    assert await count_unread_matches(session, saved_search) == 0
    assert await run_saved_search(session, saved_search, limit=20, offset=0) == []


async def test_the_unread_count_ignores_articles_already_read(session: AsyncSession) -> None:
    user = await _reader(session)
    feed = await _feed(session, user)
    saved_search = await create_saved_search(
        session, user.id, name="Rust", filters=SearchFilters(query="rust"), is_alert=False
    )
    unread = await _article(session, feed, title="Learning Rust")
    read = await _article(session, feed, title="Rust in production")
    await set_feedback_axis(session, user.id, [read.id], axis=FeedbackAxis.READ, value=True)

    assert await count_unread_matches(session, saved_search) == 1
    matched_ids = {
        article.id for article in await run_saved_search(session, saved_search, limit=20, offset=0)
    }
    assert matched_ids == {unread.id, read.id}
