import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from arq import Retry
from arq.worker import Function, func

from api.domain.webhook.models import DeliveryStatus, OutboundWebhook, WebhookDelivery
from api.technical.crypto.secret_box import decrypt_secret
from api.technical.net.url_guard import (
    BlockedUrlError,
    Resolver,
    ensure_public_http_url,
    resolve_with_system,
)
from worker.technical.db import worker_session

logger = logging.getLogger(__name__)

MAX_TRIES = 5
#: Seconds to wait before try 2, 3, 4 and 5: a receiver that is rebooting is given time to come
#: back, and one that is down for the afternoon is not hammered meanwhile.
BACKOFF_SECONDS = (30, 120, 600, 3600)
TIMEOUT_SECONDS = 10.0
SIGNATURE_HEADER = "X-Lumia-Signature"
TIMESTAMP_HEADER = "X-Lumia-Timestamp"
EVENT_HEADER = "X-Lumia-Event"
DELIVERY_HEADER = "X-Lumia-Delivery"
_USER_AGENT = "LumiaWebhooks/1.0"
_WEBHOOK_GONE = "webhook removed or disabled"
_RETRYABLE_CLIENT_ERRORS = frozenset({408, 425, 429})


def sign(secret: str, timestamp: str, body: bytes) -> str:
    """HMAC-SHA256 over `{timestamp}.{body}`: binding the timestamp lets a receiver refuse a
    captured delivery replayed later, which a signature over the body alone cannot do."""
    message = timestamp.encode() + b"." + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


async def deliver_webhook(
    ctx: dict[Any, Any],
    delivery_id: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    resolve: Resolver = resolve_with_system,
) -> None:
    """Posts one signed event to its webhook, retrying with a growing delay and then giving up
    loudly: the delivery row ends FAILED with its last error rather than the job just dying.
    """
    async with worker_session() as session:
        delivery = await session.get(WebhookDelivery, UUID(delivery_id))
        if delivery is None or delivery.status is not DeliveryStatus.PENDING:
            return
        webhook = await session.get(OutboundWebhook, delivery.webhook_id)
        if webhook is None or not webhook.active:
            delivery.status = DeliveryStatus.FAILED
            delivery.last_error = _WEBHOOK_GONE
            await session.commit()
            return

        delivery.attempts += 1
        failure, retryable = await _attempt(delivery, webhook, transport, resolve)
        if failure is None:
            delivery.status = DeliveryStatus.DELIVERED
            delivery.delivered_at = datetime.now(UTC)
            delivery.last_error = None
            await session.commit()
            return

        delivery.last_error = failure
        tries = int(ctx.get("job_try", delivery.attempts))
        give_up = not retryable or tries >= MAX_TRIES
        if give_up:
            delivery.status = DeliveryStatus.FAILED
            logger.warning("webhook delivery %s abandoned: %s", delivery_id, failure)
        await session.commit()
        if not give_up:
            raise Retry(defer=BACKOFF_SECONDS[min(tries, len(BACKOFF_SECONDS)) - 1])


async def _attempt(
    delivery: WebhookDelivery,
    webhook: OutboundWebhook,
    transport: httpx.AsyncBaseTransport | None,
    resolve: Resolver,
) -> tuple[str | None, bool]:
    try:
        await asyncio.to_thread(ensure_public_http_url, webhook.url, resolve=resolve)
    except BlockedUrlError as exc:
        return f"blocked: {exc}", False

    body = json.dumps(delivery.payload, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    headers = {
        "Content-Type": "application/json",
        "User-Agent": _USER_AGENT,
        EVENT_HEADER: delivery.event,
        DELIVERY_HEADER: str(delivery.id),
        TIMESTAMP_HEADER: timestamp,
        SIGNATURE_HEADER: f"sha256={sign(decrypt_secret(webhook.secret_encrypted), timestamp, body)}",
    }
    try:
        async with httpx.AsyncClient(
            transport=transport, timeout=TIMEOUT_SECONDS, follow_redirects=False
        ) as client:
            response = await client.post(webhook.url, content=body, headers=headers)
    except httpx.HTTPError as exc:
        delivery.last_status_code = None
        return f"{type(exc).__name__}: {exc}"[:500], True

    delivery.last_status_code = response.status_code
    if response.is_success:
        return None, False
    retryable = response.status_code >= 500 or response.status_code in _RETRYABLE_CLIENT_ERRORS
    return f"HTTP {response.status_code}", retryable


deliver_webhook_function: Function = func(deliver_webhook, max_tries=MAX_TRIES)
