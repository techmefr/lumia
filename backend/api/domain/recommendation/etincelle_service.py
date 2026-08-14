from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.feed.models import Feed
from api.domain.recommendation.models import FilterMode, UserArticleFeedback
from api.domain.recommendation.relevance import (
    load_rule_terms,
    matches_any_term,
    score_articles,
)


async def list_etincelle(
    session: AsyncSession, user_id: UUID, *, limit: int = 20, offset: int = 0
) -> list[tuple[Article, float]]:
    voted_article_ids = select(UserArticleFeedback.article_id).where(
        UserArticleFeedback.user_id == user_id,
        UserArticleFeedback.sentiment.is_not(None),
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

    muted = await load_rule_terms(session, user_id, FilterMode.MUTE)
    if muted:
        articles = [article for article in articles if not matches_any_term(article, muted)]
        if not articles:
            return []

    scores = await score_articles(session, user_id, articles)
    ranked = [(article, scores.get(article.id, 0.0)) for article in articles]
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return ranked[offset : offset + limit]
