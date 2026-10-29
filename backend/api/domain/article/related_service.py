from uuid import UUID

from sqlalchemy import Float, Select, case, cast, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api.domain.article.models import Article, ArticleKeyword
from api.domain.feed.models import Feed
from api.domain.recommendation.models import UserArticleFeedback

RELATED_LIMIT = 5
AUTHOR_WEIGHT = 1.0
CATEGORY_WEIGHT = 0.5


def _shared_keyword_weight(article_id: UUID) -> Select[UUID, float]:
    other = aliased(ArticleKeyword)
    own_keywords = select(ArticleKeyword.keyword_id).where(ArticleKeyword.article_id == article_id)
    return (
        select(other.article_id, func.sum(other.weight).label("weight"))
        .where(other.keyword_id.in_(own_keywords), other.article_id != article_id)
        .group_by(other.article_id)
    )


async def find_related_articles(
    session: AsyncSession, user_id: UUID, article: Article, limit: int = RELATED_LIMIT
) -> list[Article]:
    """Ranks the reader's other articles by shared keyword weight, author and category.

    One query: unread only, and anything sharing the canonical url is the same piece republished
    by another feed, so it is dropped rather than offered as further reading.
    """
    shared = _shared_keyword_weight(article.id).subquery()
    zero = cast(literal(0.0), Float)
    author_score = (
        case((Article.author_id == article.author_id, AUTHOR_WEIGHT), else_=0.0)
        if article.author_id is not None
        else zero
    )
    category_score = (
        case((Article.category_id == article.category_id, CATEGORY_WEIGHT), else_=0.0)
        if article.category_id is not None
        else zero
    )
    score = func.coalesce(shared.c.weight, 0.0) + author_score + category_score
    already_read = select(UserArticleFeedback.article_id).where(
        UserArticleFeedback.user_id == user_id,
        UserArticleFeedback.article_id == Article.id,
        UserArticleFeedback.read.is_(True),
    )
    query = (
        select(Article)
        .join(Feed, Feed.id == Article.feed_id)
        .outerjoin(shared, shared.c.article_id == Article.id)
        .where(
            Feed.user_id == user_id,
            Article.id != article.id,
            Article.canonical_url != article.canonical_url,
            ~already_read.exists(),
            score > 0,
        )
        .order_by(score.desc(), Article.published_at.desc())
        .limit(limit)
    )
    return list(await session.scalars(query))
