from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article, ArticleKeyword
from api.domain.recommendation.models import (
    UserArticleFeedback,
    UserAuthorScore,
    UserCategoryScore,
    UserFeedScore,
    UserKeywordScore,
    Vote,
)

_VOTE_DELTA: dict[Vote, float] = {Vote.LIKE: 1.5, Vote.DISLIKE: -0.5}


async def apply_feedback(
    session: AsyncSession, *, user_id: UUID, article_id: UUID, vote: Vote
) -> None:
    existing = await session.scalar(
        select(UserArticleFeedback).where(
            UserArticleFeedback.user_id == user_id,
            UserArticleFeedback.article_id == article_id,
        )
    )
    if existing is not None:
        previous_delta = _VOTE_DELTA.get(existing.vote, 0.0)
        if previous_delta:
            await _apply_delta(session, user_id, article_id, -previous_delta)
        existing.vote = vote
    else:
        session.add(UserArticleFeedback(user_id=user_id, article_id=article_id, vote=vote))

    new_delta = _VOTE_DELTA.get(vote, 0.0)
    if new_delta:
        await _apply_delta(session, user_id, article_id, new_delta)

    await session.commit()


async def _apply_delta(
    session: AsyncSession, user_id: UUID, article_id: UUID, delta: float
) -> None:
    article = await session.get(Article, article_id)
    if article is None:
        return

    keyword_ids = await session.scalars(
        select(ArticleKeyword.keyword_id).where(ArticleKeyword.article_id == article_id)
    )
    for keyword_id in keyword_ids:
        await _apply_keyword_delta(session, user_id, keyword_id, delta)

    await _apply_feed_delta(session, user_id, article.feed_id, delta)
    if article.author_id is not None:
        await _apply_author_delta(session, user_id, article.author_id, delta)
    if article.category_id is not None:
        await _apply_category_delta(session, user_id, article.category_id, delta)


async def _apply_keyword_delta(
    session: AsyncSession, user_id: UUID, keyword_id: UUID, delta: float
) -> None:
    row = await session.scalar(
        select(UserKeywordScore).where(
            UserKeywordScore.user_id == user_id, UserKeywordScore.keyword_id == keyword_id
        )
    )
    if row is None:
        row = UserKeywordScore(user_id=user_id, keyword_id=keyword_id, score=0.0)
        session.add(row)
    row.score += delta


async def _apply_feed_delta(
    session: AsyncSession, user_id: UUID, feed_id: UUID, delta: float
) -> None:
    row = await session.scalar(
        select(UserFeedScore).where(
            UserFeedScore.user_id == user_id, UserFeedScore.feed_id == feed_id
        )
    )
    if row is None:
        row = UserFeedScore(user_id=user_id, feed_id=feed_id, score=0.0)
        session.add(row)
    row.score += delta


async def _apply_author_delta(
    session: AsyncSession, user_id: UUID, author_id: UUID, delta: float
) -> None:
    row = await session.scalar(
        select(UserAuthorScore).where(
            UserAuthorScore.user_id == user_id, UserAuthorScore.author_id == author_id
        )
    )
    if row is None:
        row = UserAuthorScore(user_id=user_id, author_id=author_id, score=0.0)
        session.add(row)
    row.score += delta


async def _apply_category_delta(
    session: AsyncSession, user_id: UUID, category_id: UUID, delta: float
) -> None:
    row = await session.scalar(
        select(UserCategoryScore).where(
            UserCategoryScore.user_id == user_id, UserCategoryScore.category_id == category_id
        )
    )
    if row is None:
        row = UserCategoryScore(user_id=user_id, category_id=category_id, score=0.0)
        session.add(row)
    row.score += delta
