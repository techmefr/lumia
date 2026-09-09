"""Builds a playlist that fits the time the reader actually has."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.article.reading_time import estimate_reading_minutes
from api.domain.feed.models import Feed
from api.domain.playlist.models import Playlist, PlaylistItem
from api.domain.recommendation.models import FilterMode, UserArticleFeedback
from api.domain.recommendation.relevance import (
    load_rule_terms,
    matches_any_term,
    score_articles,
)

#: How many recent unread articles are considered. Same reasoning as the article list: the ranking
#: happens in Python, so the pool has to be bounded somewhere.
_POOL = 300


async def build_for_duration(
    session: AsyncSession, user_id: UUID, *, target_minutes: int
) -> Playlist:
    """Fills a new playlist with the best-scored unread articles that fit in `target_minutes`.

    Greedy over the relevance order rather than an exact bin-packing: the point is a good queue for
    a train ride, and reading-time estimates are themselves approximate, so squeezing the last
    minute out would be false precision.
    """
    read_rows = select(UserArticleFeedback.article_id).where(
        UserArticleFeedback.user_id == user_id,
        UserArticleFeedback.article_id == Article.id,
        UserArticleFeedback.read.is_(True),
    )
    candidates = list(
        await session.scalars(
            select(Article)
            .join(Feed, Feed.id == Article.feed_id)
            .where(Feed.user_id == user_id, ~read_rows.exists())
            .order_by(Article.published_at.desc())
            .limit(_POOL)
        )
    )

    muted = await load_rule_terms(session, user_id, FilterMode.MUTE)
    if muted:
        candidates = [a for a in candidates if not matches_any_term(a, muted)]

    scores = await score_articles(session, user_id, candidates)
    candidates.sort(key=lambda a: (scores.get(a.id, 0.0), a.published_at), reverse=True)

    playlist = Playlist(user_id=user_id, name=_name_for(target_minutes))
    session.add(playlist)
    await session.flush()

    remaining = target_minutes
    position = 0
    for article in candidates:
        minutes = estimate_reading_minutes(article.content)
        if minutes > remaining:
            continue
        session.add(PlaylistItem(playlist_id=playlist.id, article_id=article.id, position=position))
        position += 1
        remaining -= minutes
        if remaining <= 0:
            break

    await session.commit()
    await session.refresh(playlist, ["items"])
    return playlist


def _name_for(target_minutes: int) -> str:
    stamp = datetime.now(UTC).strftime("%d/%m")
    return f"{target_minutes} min · {stamp}"
