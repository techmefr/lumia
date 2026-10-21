from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.bulk_feedback_service import FeedbackAxis, set_feedback_axis
from api.domain.recommendation.feedback_service import apply_feedback
from api.domain.recommendation.models import UserArticleFeedback
from api.domain.user.models import Instance, User
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as open_session:
        yield open_session


async def _article_and_user(session: AsyncSession) -> tuple[Article, User]:
    instance = Instance(max_accounts=5, disk_quota_mb=100)
    session.add(instance)
    await session.flush()
    user = User(instance_id=instance.id, email="a@example.com", username="a")
    session.add(user)
    await session.flush()
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="1",
        title="Feed",
        url="https://example.com/feed",
    )
    session.add(feed)
    await session.flush()
    article = Article(
        feed_id=feed.id,
        external_entry_id="1",
        title="T",
        url="https://example.com/1",
        content="c",
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
    )
    session.add(article)
    await session.commit()
    return article, user


async def _row(session: AsyncSession, user: User, article: Article) -> UserArticleFeedback:
    return (await session.scalars(select(UserArticleFeedback))).one()


async def test_marking_read_through_feedback_stamps_the_moment(session: AsyncSession) -> None:
    article, user = await _article_and_user(session)

    await apply_feedback(session, user_id=user.id, article_id=article.id, read=True)

    assert (await _row(session, user, article)).read_at is not None


async def test_marking_unread_through_feedback_clears_the_moment(session: AsyncSession) -> None:
    article, user = await _article_and_user(session)
    await apply_feedback(session, user_id=user.id, article_id=article.id, read=True)

    await apply_feedback(session, user_id=user.id, article_id=article.id, read=False)

    assert (await _row(session, user, article)).read_at is None


async def test_other_feedback_leaves_the_read_moment_unset(session: AsyncSession) -> None:
    article, user = await _article_and_user(session)

    await apply_feedback(session, user_id=user.id, article_id=article.id, favorite=True)

    assert (await _row(session, user, article)).read_at is None


async def test_bulk_read_stamps_and_bulk_unread_clears(session: AsyncSession) -> None:
    article, user = await _article_and_user(session)

    await set_feedback_axis(session, user.id, [article.id], axis=FeedbackAxis.READ, value=True)
    assert (await _row(session, user, article)).read_at is not None

    await set_feedback_axis(session, user.id, [article.id], axis=FeedbackAxis.READ, value=False)
    await session.refresh(await _row(session, user, article))
    assert (await _row(session, user, article)).read_at is None


async def test_bulk_favorite_does_not_stamp_a_read_moment(session: AsyncSession) -> None:
    article, user = await _article_and_user(session)

    await set_feedback_axis(session, user.id, [article.id], axis=FeedbackAxis.FAVORITE, value=True)

    assert (await _row(session, user, article)).read_at is None
