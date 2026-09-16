import logging
from datetime import UTC, datetime

import aiosmtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.digest.schedule import is_due, period_key, reader_zone, window_start
from api.domain.feed.models import Feed
from api.domain.recommendation.models import FilterMode, UserArticleFeedback
from api.domain.recommendation.relevance import (
    load_rule_terms,
    matches_any_term,
    score_articles,
)
from api.domain.user.models import DigestFrequency, User
from api.technical.email.digest_messages import DigestItem, render_digest_email
from api.technical.email.smtp import send_email
from config.digest import get_digest_config
from config.email import get_email_config

logger = logging.getLogger(__name__)

SETTINGS_PATH = "/settings#digest"


async def collect_digest_items(
    session: AsyncSession, user: User, *, since: datetime
) -> list[DigestItem]:
    """The reader's best unread articles since `since`, in the order the feed would rank them.

    Same ranking as L'Étincelle rather than a fresh "most recent" query: a digest whose job is to
    be worth opening has to lead with what the reader cares about, and that judgement already
    exists. Recency only breaks ties.
    """
    read_rows = select(UserArticleFeedback.article_id).where(
        UserArticleFeedback.user_id == user.id,
        UserArticleFeedback.article_id == Article.id,
        UserArticleFeedback.read.is_(True),
    )
    articles = list(
        await session.scalars(
            select(Article)
            .join(Feed, Feed.id == Article.feed_id)
            .where(Feed.user_id == user.id, Article.published_at >= since)
            .where(~read_rows.exists())
        )
    )
    if not articles:
        return []

    muted = await load_rule_terms(session, user.id, FilterMode.MUTE)
    if muted:
        articles = [article for article in articles if not matches_any_term(article, muted)]
        if not articles:
            return []

    scores = await score_articles(session, user.id, articles)
    articles.sort(key=lambda a: (scores.get(a.id, 0.0), a.published_at), reverse=True)
    return [_to_item(article) for article in articles[: get_digest_config().digest_max_articles]]


async def send_digest(session: AsyncSession, user: User, *, now: datetime) -> bool:
    """Mails one reader their digest and records the period it covered.

    Returns whether anything was sent. An empty selection is not mailed at all: an inbox that
    receives "nothing to report" every morning teaches the reader to filter the sender away. The
    period is left unspent in that case, so a later run in the same period can still find
    something and send it.
    """
    items = await collect_digest_items(session, user, since=window_start(user, now))
    if not items:
        logger.info("digest skipped, nothing unread worth reporting")
        return False

    frontend_url = get_email_config().frontend_url.rstrip("/")
    content = render_digest_email(
        language=user.preferred_language,
        frequency=user.digest_frequency,
        items=items,
        settings_url=f"{frontend_url}{SETTINGS_PATH}",
    )
    await send_email(
        to=user.email,
        subject=content.subject,
        body=content.text_body,
        html_body=content.html_body,
    )

    local_now = now.astimezone(reader_zone(user.digest_timezone))
    user.digest_last_period = period_key(user.digest_frequency, local_now)
    user.digest_last_sent_at = now
    await session.commit()
    logger.info("digest sent with %d articles", len(items))
    return True


async def send_due_digests(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Runs one pass over the readers who opted in, and returns how many mails went out."""
    moment = now or datetime.now(UTC)
    subscribers = list(
        await session.scalars(select(User).where(User.digest_frequency != DigestFrequency.NEVER))
    )
    sent = 0
    for user in subscribers:
        if not is_due(user, moment):
            continue
        try:
            if await send_digest(session, user, now=moment):
                sent += 1
        except (aiosmtplib.SMTPException, OSError):
            # One unreachable mailbox must not cost the other subscribers their digest, and the
            # period stays unspent so the next pass retries.
            logger.warning("digest delivery failed for one reader", exc_info=True)
    return sent


def _to_item(article: Article) -> DigestItem:
    return DigestItem(
        title=article.title,
        url=article.url,
        source=article.feed.title,
        summary=article.summary,
    )
