from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.feed.models import Feed, Folder
from api.domain.recommendation.bulk_feedback_service import FeedbackAxis, set_feedback_axis
from api.domain.user.models import User

# The largest batch of items a call returns, matching what real Fever clients paginate by.
ITEMS_PAGE_SIZE = 50


async def build_groups_payload(session: AsyncSession, user: User) -> dict[str, Any]:
    folder_ids = await _ordered_ids(session, Folder.id, Folder.user_id == user.id, Folder.id)
    feed_ids = await _ordered_ids(session, Feed.id, Feed.user_id == user.id, Feed.id)
    folders = await session.scalars(select(Folder).where(Folder.user_id == user.id))
    folders_by_id = {folder.id: folder for folder in folders}
    feeds_by_folder = await session.scalars(
        select(Feed).where(Feed.user_id == user.id, Feed.folder_id.isnot(None))
    )

    groups = [
        {"id": folder_ids[folder_id], "title": folders_by_id[folder_id].name}
        for folder_id in folder_ids
    ]
    feeds_groups: dict[int, list[int]] = {}
    for feed in feeds_by_folder:
        assert feed.folder_id is not None
        group_id = folder_ids[feed.folder_id]
        feeds_groups.setdefault(group_id, []).append(feed_ids[feed.id])

    return {
        "groups": groups,
        "feeds_groups": [
            {"group_id": group_id, "feed_ids": ",".join(str(fid) for fid in sorted(members))}
            for group_id, members in feeds_groups.items()
        ],
    }


async def build_feeds_payload(session: AsyncSession, user: User) -> dict[str, Any]:
    feed_ids = await _ordered_ids(session, Feed.id, Feed.user_id == user.id, Feed.id)
    folder_ids = await _ordered_ids(session, Folder.id, Folder.user_id == user.id, Folder.id)
    feeds = await session.scalars(select(Feed).where(Feed.user_id == user.id))

    feed_list = []
    feeds_groups: dict[int, list[int]] = {}
    for feed in feeds:
        feed_list.append(
            {
                "id": feed_ids[feed.id],
                "favicon_id": 0,
                "title": feed.title,
                "url": feed.url,
                "site_url": feed.url,
                "is_spark": 0,
                "last_updated_on_time": int(
                    (feed.last_refreshed_at or feed.created_at).timestamp()
                ),
            }
        )
        if feed.folder_id is not None:
            group_id = folder_ids[feed.folder_id]
            feeds_groups.setdefault(group_id, []).append(feed_ids[feed.id])

    return {
        "feeds": feed_list,
        "feeds_groups": [
            {"group_id": group_id, "feed_ids": ",".join(str(fid) for fid in sorted(members))}
            for group_id, members in feeds_groups.items()
        ],
    }


async def _ordered_ids(
    session: AsyncSession, id_column: Any, where_clause: Any, order_by: Any
) -> dict[UUID, int]:
    """Fever wants small integer ids; Lumia's are UUIDs. Assigning them by a stable sort order
    keeps the same UUID mapped to the same integer across calls, which is all Fever's protocol
    needs: it never asks the server to guarantee ids survive forever, only that they are usable
    within a session of calls."""
    rows = await session.scalars(select(id_column).where(where_clause).order_by(order_by))
    return {row_id: index + 1 for index, row_id in enumerate(rows)}


async def _user_feed_ids(session: AsyncSession, user: User) -> list[UUID]:
    return list(await session.scalars(select(Feed.id).where(Feed.user_id == user.id)))


async def build_unread_item_ids_payload(session: AsyncSession, user: User) -> dict[str, Any]:
    ids = await _feedback_article_ids(session, user, axis=FeedbackAxis.READ, value=False)
    return {"unread_item_ids": ",".join(str(item_id) for item_id in ids)}


async def build_saved_item_ids_payload(session: AsyncSession, user: User) -> dict[str, Any]:
    ids = await _feedback_article_ids(session, user, axis=FeedbackAxis.SAVED, value=True)
    return {"saved_item_ids": ",".join(str(item_id) for item_id in ids)}


async def _feedback_article_ids(
    session: AsyncSession, user: User, *, axis: FeedbackAxis, value: bool
) -> list[int]:
    from api.domain.recommendation.models import UserArticleFeedback

    feed_ids = await _user_feed_ids(session, user)
    if not feed_ids:
        return []
    item_ids = await _ordered_item_ids(session, feed_ids)

    column = getattr(UserArticleFeedback, axis.value)
    if value:
        matching = await session.scalars(
            select(UserArticleFeedback.article_id).where(
                UserArticleFeedback.user_id == user.id, column.is_(True)
            )
        )
        matching_ids = set(matching)
        return [item_ids[article_id] for article_id in item_ids if article_id in matching_ids]

    excluded = await session.scalars(
        select(UserArticleFeedback.article_id).where(
            UserArticleFeedback.user_id == user.id, column.is_(True)
        )
    )
    excluded_ids = set(excluded)
    return [item_ids[article_id] for article_id in item_ids if article_id not in excluded_ids]


async def _ordered_item_ids(session: AsyncSession, feed_ids: Sequence[UUID]) -> dict[UUID, int]:
    rows = await session.scalars(
        select(Article.id)
        .where(Article.feed_id.in_(feed_ids))
        .order_by(Article.published_at, Article.id)
    )
    return {row_id: index + 1 for index, row_id in enumerate(rows)}


async def build_items_payload(
    session: AsyncSession,
    user: User,
    *,
    since_id: int | None,
    max_id: int | None,
    with_ids: str | None,
) -> dict[str, Any]:
    from api.domain.recommendation.models import UserArticleFeedback

    feed_ids = await _user_feed_ids(session, user)
    if not feed_ids:
        return {"items": [], "total_items": 0}

    item_ids = await _ordered_item_ids(session, feed_ids)
    reverse_ids = {int_id: article_id for article_id, int_id in item_ids.items()}
    feed_int_ids = await _ordered_ids(session, Feed.id, Feed.user_id == user.id, Feed.id)

    if with_ids:
        wanted = {int(raw) for raw in with_ids.split(",") if raw.strip().isdigit()}
        selected = sorted(wanted & reverse_ids.keys())
    else:
        candidates = sorted(reverse_ids)
        if since_id is not None:
            candidates = [item_id for item_id in candidates if item_id > since_id]
        if max_id is not None:
            candidates = [item_id for item_id in candidates if item_id < max_id]
        selected = candidates[:ITEMS_PAGE_SIZE]

    article_ids = [reverse_ids[item_id] for item_id in selected]
    articles = {
        article.id: article
        for article in await session.scalars(select(Article).where(Article.id.in_(article_ids)))
    }
    feedback = {
        row.article_id: row
        for row in await session.scalars(
            select(UserArticleFeedback).where(
                UserArticleFeedback.user_id == user.id,
                UserArticleFeedback.article_id.in_(article_ids),
            )
        )
    }

    items = []
    for item_id in selected:
        article = articles[reverse_ids[item_id]]
        state = feedback.get(article.id)
        items.append(
            {
                "id": item_id,
                "feed_id": feed_int_ids[article.feed_id],
                "title": article.title,
                "author": article.author.name if article.author else "",
                "html": article.content,
                "url": article.url,
                "is_saved": 1 if state is not None and state.saved else 0,
                "is_read": 1 if state is not None and state.read else 0,
                "created_on_time": int(article.published_at.timestamp()),
            }
        )

    total = await session.scalar(
        select(func.count()).select_from(Article).where(Article.feed_id.in_(feed_ids))
    )
    return {"items": items, "total_items": total or 0}


async def apply_mark(
    session: AsyncSession, user: User, *, mark_type: str, mark_as: str, item_id: int
) -> None:
    """Translates one Fever `mark` call into the same feedback axis the rest of Lumia reads."""
    if mark_type not in {"item", "feed", "group"}:
        return

    article_ids = await _resolve_marked_article_ids(
        session, user, mark_type=mark_type, item_id=item_id
    )
    if not article_ids:
        return

    if mark_as == "read":
        await set_feedback_axis(session, user.id, article_ids, axis=FeedbackAxis.READ, value=True)
    elif mark_as == "unread":
        await set_feedback_axis(session, user.id, article_ids, axis=FeedbackAxis.READ, value=False)
    elif mark_as == "saved":
        await set_feedback_axis(session, user.id, article_ids, axis=FeedbackAxis.SAVED, value=True)
    elif mark_as == "unsaved":
        await set_feedback_axis(session, user.id, article_ids, axis=FeedbackAxis.SAVED, value=False)


async def _resolve_marked_article_ids(
    session: AsyncSession, user: User, *, mark_type: str, item_id: int
) -> list[UUID]:
    feed_ids = await _user_feed_ids(session, user)
    if not feed_ids:
        return []
    item_ids = await _ordered_item_ids(session, feed_ids)
    reverse_ids = {int_id: article_id for article_id, int_id in item_ids.items()}

    if mark_type == "item":
        article_id = reverse_ids.get(item_id)
        return [article_id] if article_id is not None else []

    if mark_type == "feed":
        feed_int_ids = await _ordered_ids(session, Feed.id, Feed.user_id == user.id, Feed.id)
        reverse_feed_ids = {fid: feed_id for feed_id, fid in feed_int_ids.items()}
        feed_id = reverse_feed_ids.get(item_id)
        if feed_id is None:
            return []
        return list(await session.scalars(select(Article.id).where(Article.feed_id == feed_id)))

    # group
    folder_int_ids = await _ordered_ids(session, Folder.id, Folder.user_id == user.id, Folder.id)
    reverse_folder_ids = {fid: folder_id for folder_id, fid in folder_int_ids.items()}
    folder_id = reverse_folder_ids.get(item_id)
    if folder_id is None:
        return []
    group_feed_ids = list(
        await session.scalars(
            select(Feed.id).where(Feed.user_id == user.id, Feed.folder_id == folder_id)
        )
    )
    if not group_feed_ids:
        return []
    return list(
        await session.scalars(select(Article.id).where(Article.feed_id.in_(group_feed_ids)))
    )
