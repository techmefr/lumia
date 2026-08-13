from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import UserArticleFeedback, Vote
from api.domain.recommendation.saved_service import list_saved
from api.domain.user.models import Instance, User
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _seed_user_with_feed(session: AsyncSession) -> tuple[User, Feed]:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id, email=f"{id(instance)}@example.com", username="user",
        password_hash=None,
    )
    session.add(user)
    await session.flush()
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="10",
        title="Feed",
        url="https://example.com/feed",
    )
    session.add(feed)
    await session.flush()
    return user, feed


async def _add_article(session: AsyncSession, feed: Feed, external_id: str, title: str) -> Article:
    article = Article(
        feed_id=feed.id,
        external_entry_id=external_id,
        title=title,
        url=f"https://example.com/{external_id}",
        content="Content",
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
    )
    session.add(article)
    await session.flush()
    return article


async def test_list_saved_excludes_other_users_saves(session: AsyncSession) -> None:
    user, feed = await _seed_user_with_feed(session)
    other_user, other_feed = await _seed_user_with_feed(session)

    mine = await _add_article(session, feed, "1", "Mine")
    theirs = await _add_article(session, other_feed, "2", "Theirs")
    session.add(UserArticleFeedback(user_id=user.id, article_id=mine.id, vote=Vote.SAVE))
    session.add(UserArticleFeedback(user_id=other_user.id, article_id=theirs.id, vote=Vote.SAVE))
    await session.commit()

    saved = await list_saved(session, user.id)

    assert [article.title for article in saved] == ["Mine"]


async def test_list_saved_excludes_likes_and_dislikes(session: AsyncSession) -> None:
    user, feed = await _seed_user_with_feed(session)

    saved = await _add_article(session, feed, "1", "Saved")
    liked = await _add_article(session, feed, "2", "Liked")
    session.add(UserArticleFeedback(user_id=user.id, article_id=saved.id, vote=Vote.SAVE))
    session.add(UserArticleFeedback(user_id=user.id, article_id=liked.id, vote=Vote.LIKE))
    await session.commit()

    result = await list_saved(session, user.id)

    assert [article.title for article in result] == ["Saved"]
