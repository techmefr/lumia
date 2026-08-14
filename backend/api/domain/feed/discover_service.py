"""Ranks the catalogue against what the reader has actually liked."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Category, Keyword
from api.domain.feed.discover_catalogue import CATALOGUE, CatalogueEntry
from api.domain.feed.models import Feed
from api.domain.recommendation.models import UserCategoryScore, UserKeywordScore


async def list_suggestions(
    session: AsyncSession, user_id: UUID, *, limit: int = 6
) -> list[tuple[CatalogueEntry, float]]:
    subscribed = {
        url.rstrip("/")
        for url in await session.scalars(select(Feed.url).where(Feed.user_id == user_id))
    }
    affinity = await _positive_terms(session, user_id)

    ranked = [
        (entry, _affinity_for(entry, affinity))
        for entry in CATALOGUE
        if entry.url.rstrip("/") not in subscribed
    ]
    # Ties keep the catalogue order, which is stable, rather than whatever the set iteration gave.
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return ranked[:limit]


def _affinity_for(entry: CatalogueEntry, affinity: dict[str, float]) -> float:
    return sum(affinity.get(topic, 0.0) for topic in entry.topics)


async def _positive_terms(session: AsyncSession, user_id: UUID) -> dict[str, float]:
    """Lowercased keyword and category names the reader scores positively, with their score.

    Negative scores are dropped rather than subtracted: a disliked term says nothing about a source
    that merely mentions the topic, and letting it go negative would bury half the catalogue on a
    single dislike.
    """
    terms: dict[str, float] = {}

    keyword_rows = await session.execute(
        select(Keyword.term, UserKeywordScore.score)
        .join(UserKeywordScore, UserKeywordScore.keyword_id == Keyword.id)
        .where(UserKeywordScore.user_id == user_id, UserKeywordScore.score > 0)
    )
    for term, score in keyword_rows:
        key = term.lower()
        terms[key] = max(terms.get(key, 0.0), score)

    category_rows = await session.execute(
        select(Category.name, UserCategoryScore.score)
        .join(UserCategoryScore, UserCategoryScore.category_id == Category.id)
        .where(UserCategoryScore.user_id == user_id, UserCategoryScore.score > 0)
    )
    for name, score in category_rows:
        key = name.lower()
        terms[key] = max(terms.get(key, 0.0), score)

    return terms
