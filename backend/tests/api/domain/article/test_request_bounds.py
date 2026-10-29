from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
import pytest

from api.domain.article.scope import MAX_SCOPE_ARTICLE_IDS
from api.main import app

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.parametrize(
    "path",
    ["/articles", "/articles/saved", "/articles/favorites", "/articles/etincelle"],
)
async def test_an_offset_past_the_ceiling_is_refused(client: httpx.AsyncClient, path: str) -> None:
    headers = await _headers(client)

    refused = await client.get(path, headers=headers, params={"offset": 10_001})
    accepted = await client.get(path, headers=headers, params={"offset": 10_000})

    assert refused.status_code == 422
    assert accepted.status_code == 200


async def test_the_notifications_offset_is_bounded(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.get("/notifications", headers=headers, params={"offset": 10_001})

    assert response.status_code == 422


async def test_a_scope_listing_more_ids_than_the_ceiling_is_refused(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    too_many = [str(uuid4()) for _ in range(MAX_SCOPE_ARTICLE_IDS + 1)]

    response = await client.post(
        "/articles/mark-read", headers=headers, json={"article_ids": too_many}
    )

    assert response.status_code == 422


async def test_a_scope_at_the_ceiling_is_accepted(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    at_the_limit = [str(uuid4()) for _ in range(MAX_SCOPE_ARTICLE_IDS)]

    response = await client.post(
        "/articles/mark-read", headers=headers, json={"article_ids": at_the_limit}
    )

    assert response.status_code == 200
