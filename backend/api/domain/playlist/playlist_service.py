from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.article.reading_time import estimate_reading_minutes
from api.domain.feed.models import Feed
from api.domain.playlist.exceptions import (
    ArticleNotFoundError,
    BulkItemsFailedError,
    PlaylistNotFoundError,
)
from api.domain.playlist.models import Playlist, PlaylistItem


async def get_playlist(session: AsyncSession, user_id: UUID, playlist_id: UUID) -> Playlist:
    playlist = await session.scalar(
        select(Playlist).where(Playlist.id == playlist_id, Playlist.user_id == user_id)
    )
    if playlist is None:
        raise PlaylistNotFoundError
    return playlist


async def add_article(
    session: AsyncSession, user_id: UUID, playlist_id: UUID, article_id: UUID
) -> Playlist:
    """Appends an article, ignoring a duplicate rather than failing: adding twice is a user slip,
    not an error worth surfacing."""
    playlist = await get_playlist(session, user_id, playlist_id)
    await _assert_article_belongs_to_user(session, user_id, article_id)

    if any(item.article_id == article_id for item in playlist.items):
        return playlist

    next_position = max((item.position for item in playlist.items), default=-1) + 1
    session.add(
        PlaylistItem(playlist_id=playlist.id, article_id=article_id, position=next_position)
    )
    await session.commit()
    return await _reload(session, playlist.id)


async def set_articles_present(
    session: AsyncSession,
    user_id: UUID,
    playlist_id: UUID,
    article_ids: Sequence[UUID],
    *,
    present: bool,
) -> list[UUID]:
    """Adds or removes a whole selection at once, returning the ids that actually moved.

    Staged then committed once, so a selection is never half-added. Ids already in the wanted state
    are skipped rather than raising: adding an article twice is a slip, and the undo of a bulk add
    must not remove what was already there before it.
    """
    playlist = await get_playlist(session, user_id, playlist_id)
    if not article_ids:
        return []

    by_article = {item.article_id: item for item in playlist.items}
    moved: list[UUID] = []

    try:
        if present:
            next_position = max((item.position for item in playlist.items), default=-1) + 1
            for article_id in article_ids:
                if article_id in by_article:
                    continue
                session.add(
                    PlaylistItem(
                        playlist_id=playlist.id, article_id=article_id, position=next_position
                    )
                )
                next_position += 1
                moved.append(article_id)
        else:
            removed = set(article_ids) & by_article.keys()
            for article_id in removed:
                await session.delete(by_article[article_id])
            _renumber([item for item in playlist.items if item.article_id not in removed])
            moved = [article_id for article_id in article_ids if article_id in removed]

        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise BulkItemsFailedError from exc

    return moved


async def remove_article(
    session: AsyncSession, user_id: UUID, playlist_id: UUID, article_id: UUID
) -> Playlist:
    playlist = await get_playlist(session, user_id, playlist_id)
    remaining = [item for item in playlist.items if item.article_id != article_id]
    if len(remaining) == len(playlist.items):
        raise ArticleNotFoundError

    for item in playlist.items:
        if item.article_id == article_id:
            await session.delete(item)
    _renumber(remaining)
    await session.commit()
    return await _reload(session, playlist.id)


async def reorder(
    session: AsyncSession, user_id: UUID, playlist_id: UUID, article_ids: Sequence[UUID]
) -> Playlist:
    """Applies a client-supplied order. Ids absent from the payload keep their relative order at
    the end, so a stale client can't silently drop items from the playlist."""
    playlist = await get_playlist(session, user_id, playlist_id)
    by_article = {item.article_id: item for item in playlist.items}

    ordered = [by_article[article_id] for article_id in article_ids if article_id in by_article]
    ordered += [item for item in playlist.items if item not in ordered]
    _renumber(ordered)
    await session.commit()
    return await _reload(session, playlist.id)


def total_reading_minutes(playlist: Playlist) -> int:
    return sum(estimate_reading_minutes(item.article.content) for item in playlist.items)


def _renumber(items: list[PlaylistItem]) -> None:
    for position, item in enumerate(items):
        item.position = position


async def _assert_article_belongs_to_user(
    session: AsyncSession, user_id: UUID, article_id: UUID
) -> None:
    article = await session.scalar(
        select(Article.id)
        .join(Feed, Feed.id == Article.feed_id)
        .where(Article.id == article_id, Feed.user_id == user_id)
    )
    if article is None:
        raise ArticleNotFoundError


async def _reload(session: AsyncSession, playlist_id: UUID) -> Playlist:
    """Re-selects so `items` reflects the deletions/insertions just committed."""
    playlist = await session.scalar(select(Playlist).where(Playlist.id == playlist_id))
    if playlist is None:
        raise PlaylistNotFoundError
    await session.refresh(playlist, ["items"])
    return playlist
