from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article, ArticleKeyword, Author, Category, Keyword, Lang
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.feedback_service import apply_feedback
from api.domain.recommendation.models import (
    UserArticleFeedback,
    UserAuthorScore,
    UserCategoryScore,
    UserFeedScore,
    UserKeywordScore,
    Vote,
)
from api.domain.user.models import Instance, User
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _seed_article(session: AsyncSession) -> tuple[User, Article]:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id, email="user@example.com", username="user", password_hash=None
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
    author = Author(name="Jane Doe")
    category = Category(name="Tech")
    session.add_all([feed, author, category])
    await session.flush()
    article = Article(
        feed_id=feed.id,
        author_id=author.id,
        category_id=category.id,
        external_entry_id="1",
        title="Title",
        url="https://example.com/a",
        content="Content",
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
    )
    session.add(article)
    await session.flush()
    keyword = Keyword(term="chat", lang=Lang.FR)
    session.add(keyword)
    await session.flush()
    session.add(ArticleKeyword(article_id=article.id, keyword_id=keyword.id, weight=0.8))
    await session.commit()
    return user, article


async def _scores(session: AsyncSession, user: User) -> tuple[float, float, float, float]:
    keyword_score = await session.scalar(
        select(UserKeywordScore).where(UserKeywordScore.user_id == user.id)
    )
    feed_score = await session.scalar(select(UserFeedScore).where(UserFeedScore.user_id == user.id))
    author_score = await session.scalar(
        select(UserAuthorScore).where(UserAuthorScore.user_id == user.id)
    )
    category_score = await session.scalar(
        select(UserCategoryScore).where(UserCategoryScore.user_id == user.id)
    )
    return (
        keyword_score.score if keyword_score else 0.0,
        feed_score.score if feed_score else 0.0,
        author_score.score if author_score else 0.0,
        category_score.score if category_score else 0.0,
    )


async def test_like_adds_delta_to_every_criterion(session: AsyncSession) -> None:
    user, article = await _seed_article(session)

    await apply_feedback(session, user_id=user.id, article_id=article.id, vote=Vote.LIKE)

    assert await _scores(session, user) == (1.5, 1.5, 1.5, 1.5)


async def test_dislike_subtracts_from_every_criterion(session: AsyncSession) -> None:
    user, article = await _seed_article(session)

    await apply_feedback(session, user_id=user.id, article_id=article.id, vote=Vote.DISLIKE)

    assert await _scores(session, user) == (-0.5, -0.5, -0.5, -0.5)


async def test_revote_undoes_the_previous_delta_before_applying_the_new_one(
    session: AsyncSession,
) -> None:
    user, article = await _seed_article(session)

    await apply_feedback(session, user_id=user.id, article_id=article.id, vote=Vote.LIKE)
    await apply_feedback(session, user_id=user.id, article_id=article.id, vote=Vote.DISLIKE)

    assert await _scores(session, user) == (-0.5, -0.5, -0.5, -0.5)


async def test_save_does_not_affect_any_score(session: AsyncSession) -> None:
    user, article = await _seed_article(session)

    await apply_feedback(session, user_id=user.id, article_id=article.id, vote=Vote.SAVE)

    assert await _scores(session, user) == (0.0, 0.0, 0.0, 0.0)

    feedback = await session.scalar(
        select(UserArticleFeedback).where(
            UserArticleFeedback.user_id == user.id, UserArticleFeedback.article_id == article.id
        )
    )
    assert feedback is not None
    assert feedback.vote == Vote.SAVE
