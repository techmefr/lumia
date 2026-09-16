"""The scope contract every bulk action over articles shares.

`mark all as read` was written to accept exactly one scope so that a client forgetting its filter
could not silently reach the whole library. Every other bulk action inherits the same rule from
here rather than restating it: a looser contract on one endpoint would give back exactly the
accident the first one was shaped to prevent.
"""

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.feed.models import Feed


class ArticleScopeRequest(BaseModel):
    """One scope, and one only. `all` still has to be passed explicitly and true rather than
    inferred from every other field being empty, so a client that simply forgot to set a scope is
    rejected instead of reaching every feed."""

    article_ids: list[UUID] | None = None
    feed_id: UUID | None = None
    folder_id: UUID | None = None
    all: bool = False

    @model_validator(mode="after")
    def check_single_scope(self) -> "ArticleScopeRequest":
        scopes = [
            self.article_ids is not None,
            self.feed_id is not None,
            self.folder_id is not None,
            self.all,
        ]
        if sum(scopes) != 1:
            raise ValueError("exactly one of article_ids, feed_id, folder_id or all is required")
        return self


async def resolve_scope_article_ids(
    session: AsyncSession,
    user_id: UUID,
    *,
    article_ids: Sequence[UUID] | None = None,
    feed_id: UUID | None = None,
    folder_id: UUID | None = None,
) -> list[UUID]:
    """Expands a scope into article ids, always restricted to this user's own feeds."""
    query = select(Article.id).join(Feed, Feed.id == Article.feed_id).where(Feed.user_id == user_id)
    if article_ids is not None:
        query = query.where(Article.id.in_(article_ids))
    if feed_id is not None:
        query = query.where(Article.feed_id == feed_id)
    if folder_id is not None:
        query = query.where(Feed.folder_id == folder_id)
    return list(await session.scalars(query))
