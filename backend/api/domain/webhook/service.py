import asyncio
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.models import User
from api.domain.webhook.exceptions import WebhookLimitReachedError, WebhookNotFoundError
from api.domain.webhook.models import OutboundWebhook, WebhookDelivery, WebhookEvent
from api.technical.auth.tokens import generate_opaque_token
from api.technical.crypto.secret_box import encrypt_secret
from api.technical.net.url_guard import Resolver, ensure_public_http_url

MAX_WEBHOOKS_PER_USER = 10
DELIVERY_HISTORY_LIMIT = 50


async def list_webhooks(session: AsyncSession, user_id: UUID) -> list[OutboundWebhook]:
    rows = await session.scalars(
        select(OutboundWebhook)
        .where(OutboundWebhook.user_id == user_id)
        .order_by(OutboundWebhook.created_at)
    )
    return list(rows)


async def get_webhook(session: AsyncSession, user_id: UUID, webhook_id: UUID) -> OutboundWebhook:
    webhook = await session.scalar(
        select(OutboundWebhook).where(
            OutboundWebhook.id == webhook_id, OutboundWebhook.user_id == user_id
        )
    )
    if webhook is None:
        raise WebhookNotFoundError
    return webhook


async def create_webhook(
    session: AsyncSession,
    user_id: UUID,
    *,
    url: str,
    events: Sequence[WebhookEvent],
    resolve: Resolver,
) -> tuple[OutboundWebhook, str]:
    """Registers an address and returns it with its signing secret, which is shown only here.

    The address is checked against the public-URL guard now so a mistake surfaces at the form, and
    again at every delivery, because a name can be repointed at an internal address later.
    """
    await asyncio.to_thread(ensure_public_http_url, url, resolve=resolve)
    await session.execute(select(User.id).where(User.id == user_id).with_for_update())
    if len(await list_webhooks(session, user_id)) >= MAX_WEBHOOKS_PER_USER:
        raise WebhookLimitReachedError
    secret = generate_opaque_token()
    webhook = OutboundWebhook(
        user_id=user_id,
        url=url,
        secret_encrypted=encrypt_secret(secret),
        events=_distinct(events),
    )
    session.add(webhook)
    await session.commit()
    return webhook, secret


async def update_webhook(
    session: AsyncSession,
    user_id: UUID,
    webhook_id: UUID,
    *,
    url: str | None,
    events: Sequence[WebhookEvent] | None,
    active: bool | None,
    resolve: Resolver,
) -> OutboundWebhook:
    webhook = await get_webhook(session, user_id, webhook_id)
    if url is not None:
        await asyncio.to_thread(ensure_public_http_url, url, resolve=resolve)
        webhook.url = url
    if events is not None:
        webhook.events = _distinct(events)
    if active is not None:
        webhook.active = active
    await session.commit()
    return webhook


async def delete_webhook(session: AsyncSession, user_id: UUID, webhook_id: UUID) -> None:
    webhook = await get_webhook(session, user_id, webhook_id)
    await session.execute(delete(WebhookDelivery).where(WebhookDelivery.webhook_id == webhook.id))
    await session.delete(webhook)
    await session.commit()


async def list_deliveries(
    session: AsyncSession, user_id: UUID, webhook_id: UUID
) -> list[WebhookDelivery]:
    await get_webhook(session, user_id, webhook_id)
    rows = await session.scalars(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(DELIVERY_HISTORY_LIMIT)
    )
    return list(rows)


def _distinct(events: Sequence[WebhookEvent]) -> list[str]:
    return list(dict.fromkeys(event.value for event in events))
