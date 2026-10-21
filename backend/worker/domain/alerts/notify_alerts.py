from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.recommendation.models import FilterMode
from api.domain.recommendation.relevance import load_rule_terms
from api.domain.saved_search.matching import articles_matching
from api.domain.saved_search.models import AlertNotification, SavedSearch


async def notify_matching_alerts(session: AsyncSession, article: Article, *, user_id: UUID) -> None:
    """Records one notification per alert the freshly stored article satisfies.

    The article is tested against each alert in the database, with the very query the saved-search
    view runs, so an alert can never fire on something the view would not list. Only the new article
    is ever evaluated: nothing scans the library on a tick. The conflict clause makes a replayed
    job harmless on top of the early return enrichment already makes for a known article.
    """
    alerts = list(
        await session.scalars(
            select(SavedSearch).where(SavedSearch.user_id == user_id, SavedSearch.alert.is_(True))
        )
    )
    if not alerts:
        return
    muted = await load_rule_terms(session, user_id, FilterMode.MUTE)
    for search in alerts:
        hit = await session.scalar(
            articles_matching(search, muted_terms=muted).where(Article.id == article.id)
        )
        if hit is None:
            continue
        await session.execute(
            insert(AlertNotification)
            .values(user_id=user_id, saved_search_id=search.id, article_id=article.id)
            .on_conflict_do_nothing(constraint="uq_alert_notifications_search_article")
        )
