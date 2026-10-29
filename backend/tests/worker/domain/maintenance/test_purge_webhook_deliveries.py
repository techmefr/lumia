from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.models import Instance, User
from api.domain.webhook.models import (
    DeliveryStatus,
    OutboundWebhook,
    WebhookDelivery,
    WebhookEvent,
)
from config.database import get_engine
from config.maintenance import get_maintenance_config
from worker.domain.maintenance.purge_webhook_deliveries import purge_old_webhook_deliveries

RETENTION = timedelta(days=get_maintenance_config().webhook_delivery_retention_days)


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as db_session:
        yield db_session


async def _webhook(session: AsyncSession) -> OutboundWebhook:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(instance_id=instance.id, email=f"{uuid4()}@example.com", username="reader")
    session.add(user)
    await session.flush()
    webhook = OutboundWebhook(
        user_id=user.id,
        url="https://hooks.example.com/in",
        secret_encrypted="x",
        events=[WebhookEvent.ARTICLE_SAVED.value],
    )
    session.add(webhook)
    await session.flush()
    return webhook


def _delivery(webhook: OutboundWebhook, status: DeliveryStatus, age: timedelta) -> WebhookDelivery:
    return WebhookDelivery(
        webhook_id=webhook.id,
        event=WebhookEvent.ARTICLE_SAVED.value,
        payload={},
        status=status,
        created_at=datetime.now(UTC) - age,
    )


async def test_old_settled_deliveries_are_deleted(session: AsyncSession) -> None:
    webhook = await _webhook(session)
    old = timedelta(days=1) + RETENTION
    session.add_all(
        [
            _delivery(webhook, DeliveryStatus.DELIVERED, old),
            _delivery(webhook, DeliveryStatus.FAILED, old),
        ]
    )
    await session.commit()

    assert await purge_old_webhook_deliveries({}) == 2

    assert (await session.scalars(select(WebhookDelivery))).all() == []


async def test_recent_and_pending_deliveries_survive(session: AsyncSession) -> None:
    webhook = await _webhook(session)
    session.add_all(
        [
            _delivery(webhook, DeliveryStatus.DELIVERED, timedelta(days=1)),
            _delivery(webhook, DeliveryStatus.PENDING, RETENTION + timedelta(days=1)),
        ]
    )
    await session.commit()

    assert await purge_old_webhook_deliveries({}) == 0

    assert len((await session.scalars(select(WebhookDelivery))).all()) == 2


async def test_purging_an_empty_table_is_a_no_op(session: AsyncSession) -> None:
    assert await purge_old_webhook_deliveries({}) == 0
