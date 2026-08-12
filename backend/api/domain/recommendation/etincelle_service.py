from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article, ArticleKeyword
from api.domain.feed.models import Feed
from api.domain.recommendation.models import (
    UserArticleFeedback,
    UserAuthorScore,
    UserCategoryScore,
    UserFeedScore,
    UserKeywordScore,
)


async def list_etincelle(
    session: AsyncSession, user_id: UUID, *, limit: int = 20, offset: int = 0
) -> list[tuple[Article, float]]:
    voted_article_ids = select(UserArticleFeedback.article_id).where(
        UserArticleFeedback.user_id == user_id
    )
    articles = list(
        await session.scalars(
            select(Article)
            .join(Feed, Feed.id == Article.feed_id)
            .where(Feed.user_id == user_id, Article.id.not_in(voted_article_ids))
        )
    )
    if not articles:
        return []

    keywords_by_article, keyword_scores = await _load_keyword_scores(session, user_id, articles)
    feed_scores = await _load_feed_scores(
        session, user_id, {article.feed_id for article in articles}
    )
    author_ids = {article.author_id for article in articles if article.author_id is not None}
    author_scores = await _load_author_scores(session, user_id, author_ids)
    category_ids = {
        article.category_id for article in articles if article.category_id is not None
    }
    category_scores = await _load_category_scores(session, user_id, category_ids)

    ranked = [
        (
            article,
            _average_score(
                article, keywords_by_article, keyword_scores, feed_scores, author_scores,
                category_scores,
            ),
        )
        for article in articles
    ]
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return ranked[offset : offset + limit]


def _average_score(
    article: Article,
    keywords_by_article: dict[UUID, list[UUID]],
    keyword_scores: dict[UUID, float],
    feed_scores: dict[UUID, float],
    author_scores: dict[UUID, float],
    category_scores: dict[UUID, float],
) -> float:
    scores = [keyword_scores.get(kid, 0.0) for kid in keywords_by_article.get(article.id, [])]
    scores.append(feed_scores.get(article.feed_id, 0.0))
    if article.author_id is not None:
        scores.append(author_scores.get(article.author_id, 0.0))
    if article.category_id is not None:
        scores.append(category_scores.get(article.category_id, 0.0))
    return sum(scores) / len(scores) if scores else 0.0


async def _load_keyword_scores(
    session: AsyncSession, user_id: UUID, articles: list[Article]
) -> tuple[dict[UUID, list[UUID]], dict[UUID, float]]:
    article_ids = [article.id for article in articles]
    rows = await session.execute(
        select(ArticleKeyword.article_id, ArticleKeyword.keyword_id).where(
            ArticleKeyword.article_id.in_(article_ids)
        )
    )
    keywords_by_article: dict[UUID, list[UUID]] = defaultdict(list)
    all_keyword_ids: set[UUID] = set()
    for article_id, keyword_id in rows:
        keywords_by_article[article_id].append(keyword_id)
        all_keyword_ids.add(keyword_id)

    if not all_keyword_ids:
        return keywords_by_article, {}

    scores = await session.scalars(
        select(UserKeywordScore).where(
            UserKeywordScore.user_id == user_id,
            UserKeywordScore.keyword_id.in_(all_keyword_ids),
        )
    )
    return keywords_by_article, {score.keyword_id: score.score for score in scores}


async def _load_feed_scores(
    session: AsyncSession, user_id: UUID, feed_ids: set[UUID]
) -> dict[UUID, float]:
    if not feed_ids:
        return {}
    rows = await session.scalars(
        select(UserFeedScore).where(
            UserFeedScore.user_id == user_id, UserFeedScore.feed_id.in_(feed_ids)
        )
    )
    return {row.feed_id: row.score for row in rows}


async def _load_author_scores(
    session: AsyncSession, user_id: UUID, author_ids: set[UUID]
) -> dict[UUID, float]:
    if not author_ids:
        return {}
    rows = await session.scalars(
        select(UserAuthorScore).where(
            UserAuthorScore.user_id == user_id, UserAuthorScore.author_id.in_(author_ids)
        )
    )
    return {row.author_id: row.score for row in rows}


async def _load_category_scores(
    session: AsyncSession, user_id: UUID, category_ids: set[UUID]
) -> dict[UUID, float]:
    if not category_ids:
        return {}
    rows = await session.scalars(
        select(UserCategoryScore).where(
            UserCategoryScore.user_id == user_id,
            UserCategoryScore.category_id.in_(category_ids),
        )
    )
    return {row.category_id: row.score for row in rows}
