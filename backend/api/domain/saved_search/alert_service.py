"""Keyword alerts: notifying a reader the moment a new article matches a saved search.

Evaluated at ingestion, once per newly created article, against that reader's own alert-enabled
saved searches only — never by sweeping the article table on a timer. The cost of an alert is
therefore proportional to how many searches a reader has turned into alerts, not to how many
articles exist, so it does not grow with the size of the library the way a periodic scan would.
"""

import logging
from uuid import UUID

import aiosmtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.article.search_filters import SearchFilters, matches_article
from api.domain.saved_search.models import SavedSearch, SavedSearchMatch
from api.domain.user.models import User
from api.technical.email.alert_messages import render_alert_email
from api.technical.email.smtp import send_email
from config.email import get_email_config

logger = logging.getLogger(__name__)

SETTINGS_PATH = "/settings#saved-searches"


def _filters_of(alert: SavedSearch) -> SearchFilters:
    return SearchFilters(
        query=alert.query,
        folder_id=alert.folder_id,
        feed_id=alert.feed_id,
        author_id=alert.author_id,
        category_id=alert.category_id,
        keyword_id=alert.keyword_id,
    )


async def evaluate_alerts_for_new_article(
    session: AsyncSession, article: Article, *, user_id: UUID, feed_title: str
) -> None:
    """Checks one freshly ingested article against its owner's keyword alerts and mails a match.

    Called from the enrichment pipeline right after the article is created, in the same session and
    ahead of its commit: the match row and the article therefore land together, so a job retried
    before that commit re-evaluates cleanly instead of leaving an orphaned match. `feed_title` is
    passed in rather than read off `article.feed`: the relationship would need its own lazy load
    right after a plain `flush()`, and the caller already has the feed in hand.
    """
    user = await session.get(User, user_id)
    if user is None:
        return

    alerts = list(
        await session.scalars(
            select(SavedSearch).where(
                SavedSearch.user_id == user_id, SavedSearch.is_alert.is_(True)
            )
        )
    )
    for alert in alerts:
        await _notify_if_matching(session, user, alert, article, feed_title)


async def _notify_if_matching(
    session: AsyncSession, user: User, alert: SavedSearch, article: Article, feed_title: str
) -> None:
    already_seen = await session.scalar(
        select(SavedSearchMatch).where(
            SavedSearchMatch.saved_search_id == alert.id,
            SavedSearchMatch.article_id == article.id,
        )
    )
    if already_seen is not None:
        return

    matched = await session.scalar(matches_article(_filters_of(alert), article.id, user.id))
    if matched is None:
        return

    session.add(SavedSearchMatch(saved_search_id=alert.id, article_id=article.id))
    await session.flush()

    frontend_url = get_email_config().frontend_url.rstrip("/")
    content = render_alert_email(
        language=user.preferred_language,
        saved_search_name=alert.name,
        title=article.title,
        url=article.url,
        source=feed_title,
        summary=article.summary,
        settings_url=f"{frontend_url}{SETTINGS_PATH}",
    )
    try:
        await send_email(
            to=user.email,
            subject=content.subject,
            body=content.text_body,
            html_body=content.html_body,
        )
    except (aiosmtplib.SMTPException, OSError):
        # The match row is already flushed, so a failed send is not retried: same trade-off as the
        # digest, where one unreachable mailbox must not stall ingestion for everyone else.
        logger.warning("keyword alert delivery failed for one reader", exc_info=True)
