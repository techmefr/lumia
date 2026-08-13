from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.feed.models import Feed
from api.domain.recommendation.models import UserArticleFeedback


async def list_favorites(
    session: AsyncSession, user_id: UUID, *, limit: int = 20, offset: int = 0
) -> list[Article]:
    query = (
        select(Article)
        .join(Feed, Feed.id == Article.feed_id)
        .join(UserArticleFeedback, UserArticleFeedback.article_id == Article.id)
        .where(
            Feed.user_id == user_id,
            UserArticleFeedback.user_id == user_id,
            UserArticleFeedback.favorite.is_(True),
        )
        .order_by(UserArticleFeedback.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(await session.scalars(query))
