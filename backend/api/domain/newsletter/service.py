import hashlib
from datetime import UTC, datetime
from email.utils import parseaddr
from html import escape
from uuid import UUID

import nh3
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.feed.models import Feed, SourceType
from api.domain.newsletter.exceptions import EmptyMessageError, UnknownInboxError
from api.domain.newsletter.models import NewsletterInbox
from api.domain.newsletter.schemas import InboundMessage
from api.domain.user.models import User
from api.technical.auth.tokens import generate_opaque_token, hash_token
from worker.technical.connectors.base import RawArticle

NEWSLETTERS_FEED_TITLE = "Newsletters"
UNTITLED_ISSUE = "(no subject)"


def newsletter_feed_external_id(user_id: UUID) -> str:
    """Enrichment matches the feeds of a MANUAL source on this id across every account, so it has
    to be unique per reader."""
    return f"newsletters:{user_id}"


async def active_inbox(session: AsyncSession, user: User) -> NewsletterInbox | None:
    inboxes = await session.scalars(
        select(NewsletterInbox).where(NewsletterInbox.user_id == user.id)
    )
    return inboxes.first()


async def create_inbox(session: AsyncSession, user: User) -> tuple[NewsletterInbox, str]:
    """Issues a fresh address and retires the previous one: a lost or leaked address stops working."""
    await revoke_inbox(session, user)
    raw_token = generate_opaque_token()
    inbox = NewsletterInbox(user_id=user.id, token_hash=hash_token(raw_token))
    session.add(inbox)
    await session.commit()
    return inbox, raw_token


async def revoke_inbox(session: AsyncSession, user: User) -> None:
    await session.execute(delete(NewsletterInbox).where(NewsletterInbox.user_id == user.id))
    await session.commit()


async def prepare_article(
    session: AsyncSession, raw_token: str, message: InboundMessage
) -> RawArticle:
    """Turns a posted mail into the article the shared enrichment pipeline expects.

    The feed is created here, before the job is queued, because enrichment only fills feeds that
    exist. The entry id comes from the message id when the forwarder gives one, so a retried
    delivery lands on the same article instead of a second copy.
    """
    inbox = await session.scalar(
        select(NewsletterInbox).where(NewsletterInbox.token_hash == hash_token(raw_token))
    )
    if inbox is None:
        raise UnknownInboxError
    body = _readable_body(message)
    external_id = newsletter_feed_external_id(inbox.user_id)
    await _ensure_feed(session, inbox.user_id, external_id)

    published_at = message.date or datetime.now(UTC)
    identity = (
        message.message_id or f"{message.sender}|{message.subject}|{published_at.isoformat()}"
    )
    entry_id = hashlib.sha256(identity.encode()).hexdigest()
    return RawArticle(
        source_type=SourceType.MANUAL.value,
        feed_external_id=external_id,
        external_entry_id=entry_id,
        title=message.subject.strip() or UNTITLED_ISSUE,
        url=f"urn:lumia:newsletter:{entry_id}",
        content=body,
        published_at=published_at,
        author_name=_sender_name(message.sender),
    )


def _readable_body(message: InboundMessage) -> str:
    if message.html and message.html.strip():
        return nh3.clean(message.html, link_rel="noopener noreferrer nofollow")
    if message.text and message.text.strip():
        blocks = [block.strip() for block in message.text.split("\n\n") if block.strip()]
        return "".join(f"<p>{escape(block)}</p>" for block in blocks)
    raise EmptyMessageError


def _sender_name(sender: str) -> str:
    name, address = parseaddr(sender)
    return (name or address or sender).strip()


async def _ensure_feed(session: AsyncSession, user_id: UUID, external_id: str) -> None:
    existing = await session.scalar(
        select(Feed.id).where(
            Feed.user_id == user_id,
            Feed.source_type == SourceType.MANUAL,
            Feed.external_feed_id == external_id,
        )
    )
    if existing is None:
        session.add(
            Feed(
                user_id=user_id,
                source_type=SourceType.MANUAL,
                external_feed_id=external_id,
                title=NEWSLETTERS_FEED_TITLE,
                url="",
            )
        )
        await session.commit()
