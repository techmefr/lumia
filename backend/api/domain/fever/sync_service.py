from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.feed.models import Feed, Folder
from api.domain.recommendation.bulk_feedback_service import FeedbackAxis, set_feedback_axis
from api.domain.recommendation.models import UserArticleFeedback

#: Items per page, fixed by the protocol: clients page with since_id until a short page comes back.
PAGE_SIZE = 50

#: Fever has no notion of a feed outside a group, and some clients hide such feeds. Feeds without a
#: folder are therefore listed under one synthetic group; the id is int32-max so it can never be
#: reached by the identity column of a real folder.
UNFILED_GROUP_ID = 2_147_483_647

#: The id Fever gives the "all items" pseudo group.
ALL_ITEMS_GROUP_ID = 0


class MarkTarget(StrEnum):
    ITEM = "item"
    FEED = "feed"
    GROUP = "group"


class MarkState(StrEnum):
    READ = "read"
    UNREAD = "unread"
    SAVED = "saved"
    UNSAVED = "unsaved"


@dataclass(frozen=True)
class FeverItem:
    id: int
    feed_id: int
    title: str
    author: str
    html: str
    url: str
    is_saved: bool
    is_read: bool
    created_on_time: int


@dataclass(frozen=True)
class FeverFeed:
    id: int
    title: str
    url: str
    last_updated_on_time: int


@dataclass(frozen=True)
class FeverGroup:
    id: int
    title: str
    feed_ids: list[int]


def epoch(moment: datetime | None) -> int:
    return int(moment.timestamp()) if moment else 0


async def last_refreshed(session: AsyncSession, user_id: UUID) -> int:
    latest = await session.scalar(
        select(func.max(Feed.last_refreshed_at)).where(Feed.user_id == user_id)
    )
    return epoch(latest or datetime.now(UTC))


async def list_feeds(session: AsyncSession, user_id: UUID) -> list[FeverFeed]:
    rows = await session.scalars(
        select(Feed).where(Feed.user_id == user_id).order_by(Feed.fever_id)
    )
    return [
        FeverFeed(
            id=feed.fever_id,
            title=feed.title,
            url=feed.url,
            last_updated_on_time=epoch(feed.last_refreshed_at),
        )
        for feed in rows
    ]


async def list_groups(session: AsyncSession, user_id: UUID) -> list[FeverGroup]:
    folders = list(
        await session.scalars(
            select(Folder).where(Folder.user_id == user_id).order_by(Folder.fever_id)
        )
    )
    feeds = list(
        await session.execute(
            select(Feed.fever_id, Feed.folder_id)
            .where(Feed.user_id == user_id)
            .order_by(Feed.fever_id)
        )
    )
    by_folder: dict[UUID | None, list[int]] = {}
    for fever_id, folder_id in feeds:
        by_folder.setdefault(folder_id, []).append(fever_id)

    groups = [
        FeverGroup(id=folder.fever_id, title=folder.name, feed_ids=by_folder.get(folder.id, []))
        for folder in folders
    ]
    if by_folder.get(None):
        groups.append(FeverGroup(id=UNFILED_GROUP_ID, title="Unfiled", feed_ids=by_folder[None]))
    return groups


def _readable_items(user_id: UUID) -> Select[tuple[Article, bool, bool]]:
    return (
        select(Article, UserArticleFeedback.read, UserArticleFeedback.saved)
        .join(Feed, Feed.id == Article.feed_id)
        .outerjoin(
            UserArticleFeedback,
            and_(
                UserArticleFeedback.article_id == Article.id,
                UserArticleFeedback.user_id == user_id,
            ),
        )
        .where(Feed.user_id == user_id)
    )


async def count_items(session: AsyncSession, user_id: UUID) -> int:
    return (
        await session.scalar(
            select(func.count())
            .select_from(Article)
            .join(Feed, Feed.id == Article.feed_id)
            .where(Feed.user_id == user_id)
        )
    ) or 0


async def list_items(
    session: AsyncSession,
    user_id: UUID,
    *,
    since_id: int | None = None,
    max_id: int | None = None,
    with_ids: Sequence[int] | None = None,
) -> list[FeverItem]:
    """One page of items, in the three shapes the protocol allows.

    `with_ids` is an explicit lookup; `since_id` walks forward from a cursor, oldest first, which
    is how a client catches up; `max_id` walks backward, newest first, and 0 means "from the top".
    Without any of them the first page from the beginning is returned, the same as `since_id=0`.
    """
    query = _readable_items(user_id)
    if with_ids is not None:
        query = query.where(Article.fever_id.in_(with_ids[:PAGE_SIZE])).order_by(Article.fever_id)
    elif max_id is not None:
        if max_id > 0:
            query = query.where(Article.fever_id < max_id)
        query = query.order_by(Article.fever_id.desc()).limit(PAGE_SIZE)
    else:
        query = (
            query.where(Article.fever_id > (since_id or 0))
            .order_by(Article.fever_id)
            .limit(PAGE_SIZE)
        )
    return [
        FeverItem(
            id=article.fever_id,
            feed_id=article.feed.fever_id,
            title=article.title,
            author=article.author.name if article.author else "",
            html=article.content,
            url=article.url,
            is_saved=bool(saved),
            is_read=bool(read),
            created_on_time=epoch(article.published_at),
        )
        for article, read, saved in await session.execute(query)
    ]


async def unread_item_ids(session: AsyncSession, user_id: UUID) -> list[int]:
    rows = await session.scalars(
        select(Article.fever_id)
        .join(Feed, Feed.id == Article.feed_id)
        .outerjoin(
            UserArticleFeedback,
            and_(
                UserArticleFeedback.article_id == Article.id,
                UserArticleFeedback.user_id == user_id,
            ),
        )
        .where(Feed.user_id == user_id, func.coalesce(UserArticleFeedback.read, False).is_(False))
        .order_by(Article.fever_id)
    )
    return list(rows)


async def saved_item_ids(session: AsyncSession, user_id: UUID) -> list[int]:
    rows = await session.scalars(
        select(Article.fever_id)
        .join(Feed, Feed.id == Article.feed_id)
        .join(
            UserArticleFeedback,
            and_(
                UserArticleFeedback.article_id == Article.id,
                UserArticleFeedback.user_id == user_id,
            ),
        )
        .where(Feed.user_id == user_id, UserArticleFeedback.saved.is_(True))
        .order_by(Article.fever_id)
    )
    return list(rows)


async def mark(
    session: AsyncSession,
    user_id: UUID,
    *,
    target: MarkTarget,
    state: MarkState,
    target_id: int,
    before: int | None,
) -> None:
    """Applies a mark, always through the reader's own articles: a foreign id matches nothing."""
    query = select(Article.id).join(Feed, Feed.id == Article.feed_id).where(Feed.user_id == user_id)
    if target is MarkTarget.ITEM:
        query = query.where(Article.fever_id == target_id)
    else:
        if state is not MarkState.READ:
            return
        if target is MarkTarget.FEED:
            query = query.where(Feed.fever_id == target_id)
        elif target_id == UNFILED_GROUP_ID:
            query = query.where(Feed.folder_id.is_(None))
        elif target_id != ALL_ITEMS_GROUP_ID:
            query = query.join(Folder, Folder.id == Feed.folder_id).where(
                Folder.fever_id == target_id
            )
        if before is not None:
            query = query.where(Article.published_at <= datetime.fromtimestamp(before, UTC))

    article_ids = list(await session.scalars(query))
    axis = (
        FeedbackAxis.SAVED if state in (MarkState.SAVED, MarkState.UNSAVED) else FeedbackAxis.READ
    )
    value = state in (MarkState.READ, MarkState.SAVED)
    await set_feedback_axis(session, user_id, article_ids, axis=axis, value=value)
