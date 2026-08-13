from collections import defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.feed.models import Feed
from api.domain.recommendation.models import UserArticleFeedback


@dataclass
class UnreadCounts:
    total: int = 0
    feeds: dict[UUID, int] = field(default_factory=dict)
    folders: dict[UUID, int] = field(default_factory=dict)


async def count_unread(session: AsyncSession, user_id: UUID) -> UnreadCounts:
    read_rows = select(UserArticleFeedback.article_id).where(
        UserArticleFeedback.user_id == user_id,
        UserArticleFeedback.article_id == Article.id,
        UserArticleFeedback.read.is_(True),
    )
    rows = await session.execute(
        select(Article.feed_id, Feed.folder_id, func.count())
        .join(Feed, Feed.id == Article.feed_id)
        .where(Feed.user_id == user_id, ~read_rows.exists())
        .group_by(Article.feed_id, Feed.folder_id)
    )

    counts = UnreadCounts()
    folders: dict[UUID, int] = defaultdict(int)
    for feed_id, folder_id, count in rows:
        counts.feeds[feed_id] = count
        counts.total += count
        if folder_id is not None:
            folders[folder_id] += count
    counts.folders = dict(folders)
    return counts
