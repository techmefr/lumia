import json
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import httpx
import pytest
from arq import Retry
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.user.models import Instance, User
from api.domain.webhook.models import DeliveryStatus, OutboundWebhook, WebhookDelivery
from api.technical.crypto.secret_box import encrypt_secret
from config.database import get_engine
from worker.domain.webhook.deliver_webhook import (
    BACKOFF_SECONDS,
    DELIVERY_HEADER,
    EVENT_HEADER,
    MAX_TRIES,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    deliver_webhook,
    sign,
)

SECRET = "s3cret"
PUBLIC = ["93.184.216.34"]


def _factory() -> async_sessionmaker:  # type: ignore[type-arg]
    return async_sessionmaker(get_engine(), expire_on_commit=False)


def _public(host: str) -> list[str]:
    return PUBLIC


class Receiver:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        def handle(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return httpx.Response(self.status_code)

        return httpx.MockTransport(handle)


@pytest.fixture
async def seeded(db_schema: None) -> AsyncIterator[tuple[UUID, UUID]]:
    async with _factory()() as session:
        instance = Instance(max_accounts=10, disk_quota_mb=1000)
        session.add(instance)
        await session.flush()
        user = User(instance_id=instance.id, email="a@example.com", username="a")
        session.add(user)
        await session.flush()
        webhook = OutboundWebhook(
            user_id=user.id,
            url="https://hooks.example.com/lumia",
            secret_encrypted=encrypt_secret(SECRET),
            events=["article.saved"],
        )
        session.add(webhook)
        await session.flush()
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event="article.saved",
            payload={"id": "x", "event": "article.saved", "article": {"title": "Été"}},
        )
        session.add(delivery)
        await session.commit()
        yield webhook.id, delivery.id


async def _reload(delivery_id: UUID) -> WebhookDelivery:
    async with _factory()() as session:
        delivery = await session.get(WebhookDelivery, delivery_id)
        assert delivery is not None
        reloaded: WebhookDelivery = delivery
        return reloaded


async def test_a_delivery_is_posted_with_a_signature_the_receiver_can_verify(
    seeded: tuple[UUID, UUID],
) -> None:
    _, delivery_id = seeded
    receiver = Receiver()

    await deliver_webhook(
        {"job_try": 1}, str(delivery_id), transport=receiver.transport(), resolve=_public
    )

    (request,) = receiver.requests
    assert request.headers[EVENT_HEADER] == "article.saved"
    assert request.headers[DELIVERY_HEADER] == str(delivery_id)
    timestamp = request.headers[TIMESTAMP_HEADER]
    expected = sign(SECRET, timestamp, request.content)
    assert request.headers[SIGNATURE_HEADER] == f"sha256={expected}"
    assert json.loads(request.content)["article"]["title"] == "Été"
    delivery = await _reload(delivery_id)
    assert delivery.status is DeliveryStatus.DELIVERED
    assert delivery.attempts == 1
    assert delivery.delivered_at is not None


async def test_a_signature_depends_on_the_timestamp_so_a_capture_cannot_be_replayed() -> None:
    assert sign(SECRET, "100", b"{}") != sign(SECRET, "101", b"{}")
    assert sign(SECRET, "100", b"{}") != sign("other", "100", b"{}")


async def test_a_failing_receiver_is_retried_with_a_growing_delay(
    seeded: tuple[UUID, UUID],
) -> None:
    _, delivery_id = seeded
    receiver = Receiver(status_code=503)

    for attempt in (1, 2):
        with pytest.raises(Retry) as retry:
            await deliver_webhook(
                {"job_try": attempt},
                str(delivery_id),
                transport=receiver.transport(),
                resolve=_public,
            )
        assert retry.value.defer_score == BACKOFF_SECONDS[attempt - 1] * 1000

    delivery = await _reload(delivery_id)
    assert delivery.status is DeliveryStatus.PENDING
    assert delivery.attempts == 2
    assert delivery.last_error == "HTTP 503"
    assert delivery.last_status_code == 503


async def test_the_last_try_gives_up_explicitly_instead_of_failing_silently(
    seeded: tuple[UUID, UUID],
) -> None:
    _, delivery_id = seeded

    await deliver_webhook(
        {"job_try": MAX_TRIES},
        str(delivery_id),
        transport=Receiver(status_code=500).transport(),
        resolve=_public,
    )

    delivery = await _reload(delivery_id)
    assert delivery.status is DeliveryStatus.FAILED
    assert delivery.last_error == "HTTP 500"


@pytest.mark.parametrize("status_code", [400, 404, 410, 302])
async def test_a_refusal_that_will_not_change_is_not_retried(
    seeded: tuple[UUID, UUID], status_code: int
) -> None:
    _, delivery_id = seeded

    await deliver_webhook(
        {"job_try": 1},
        str(delivery_id),
        transport=Receiver(status_code=status_code).transport(),
        resolve=_public,
    )

    assert (await _reload(delivery_id)).status is DeliveryStatus.FAILED


async def test_a_rate_limited_receiver_is_retried(seeded: tuple[UUID, UUID]) -> None:
    _, delivery_id = seeded

    with pytest.raises(Retry):
        await deliver_webhook(
            {"job_try": 1},
            str(delivery_id),
            transport=Receiver(status_code=429).transport(),
            resolve=_public,
        )


async def test_an_unreachable_receiver_is_retried(seeded: tuple[UUID, UUID]) -> None:
    _, delivery_id = seeded

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(Retry):
        await deliver_webhook(
            {"job_try": 1},
            str(delivery_id),
            transport=httpx.MockTransport(refuse),
            resolve=_public,
        )

    delivery = await _reload(delivery_id)
    assert delivery.last_error is not None
    assert delivery.last_error.startswith("ConnectError")
    assert delivery.last_status_code is None


async def test_an_address_that_now_points_inside_the_network_is_never_requested(
    seeded: tuple[UUID, UUID],
) -> None:
    _, delivery_id = seeded
    receiver = Receiver()

    await deliver_webhook(
        {"job_try": 1},
        str(delivery_id),
        transport=receiver.transport(),
        resolve=lambda host: ["169.254.169.254"],
    )

    assert receiver.requests == []
    delivery = await _reload(delivery_id)
    assert delivery.status is DeliveryStatus.FAILED
    assert delivery.last_error is not None
    assert delivery.last_error.startswith("blocked")


async def test_a_webhook_paused_after_the_event_receives_nothing(
    seeded: tuple[UUID, UUID],
) -> None:
    webhook_id, delivery_id = seeded
    async with _factory()() as session:
        webhook = await session.get(OutboundWebhook, webhook_id)
        assert webhook is not None
        webhook.active = False
        await session.commit()
    receiver = Receiver()

    await deliver_webhook(
        {"job_try": 1}, str(delivery_id), transport=receiver.transport(), resolve=_public
    )

    assert receiver.requests == []
    assert (await _reload(delivery_id)).status is DeliveryStatus.FAILED


async def test_a_delivery_already_settled_is_not_sent_twice(seeded: tuple[UUID, UUID]) -> None:
    _, delivery_id = seeded
    receiver = Receiver()
    for _ in range(2):
        await deliver_webhook(
            {"job_try": 1}, str(delivery_id), transport=receiver.transport(), resolve=_public
        )

    assert len(receiver.requests) == 1


async def test_an_unknown_delivery_is_ignored(db_schema: None) -> None:
    await deliver_webhook({"job_try": 1}, str(uuid4()), resolve=_public)
