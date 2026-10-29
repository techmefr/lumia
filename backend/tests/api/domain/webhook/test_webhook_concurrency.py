import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.webhook.models import OutboundWebhook, WebhookDelivery
from api.domain.webhook.service import MAX_WEBHOOKS_PER_USER
from api.main import app
from api.technical.net.url_guard import get_url_resolver
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    app.dependency_overrides[get_url_resolver] = lambda: lambda host: ["93.184.216.34"]
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_concurrent_creations_never_exceed_the_limit(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    responses = await asyncio.gather(
        *(
            client.post(
                "/outbound-webhooks",
                headers=headers,
                json={"url": f"https://hooks.example.com/{n}", "events": ["article.saved"]},
            )
            for n in range(MAX_WEBHOOKS_PER_USER + 5)
        )
    )

    statuses = sorted(response.status_code for response in responses)
    assert statuses.count(201) == MAX_WEBHOOKS_PER_USER
    assert statuses.count(409) == 5
    async with async_sessionmaker(get_engine())() as session:
        stored = await session.scalar(select(func.count()).select_from(OutboundWebhook))
    assert stored == MAX_WEBHOOKS_PER_USER


async def test_deleting_a_webhook_removes_all_its_deliveries(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    created = (
        await client.post(
            "/outbound-webhooks",
            headers=headers,
            json={"url": "https://hooks.example.com/x", "events": ["article.saved"]},
        )
    ).json()
    async with async_sessionmaker(get_engine())() as session:
        session.add_all(
            WebhookDelivery(webhook_id=created["id"], event="article.saved", payload={})
            for _ in range(3)
        )
        await session.commit()

    response = await client.delete(f"/outbound-webhooks/{created['id']}", headers=headers)

    assert response.status_code == 204
    async with async_sessionmaker(get_engine())() as session:
        assert await session.scalar(select(func.count()).select_from(WebhookDelivery)) == 0
