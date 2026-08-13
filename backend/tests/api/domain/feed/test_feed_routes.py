from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.user.models import Instance, User
from api.main import app
from api.technical.auth.jwt import create_access_token
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}

FEED_PAYLOAD = {
    "source_type": "miniflux",
    "external_feed_id": "42",
    "title": "Hacker News",
    "url": "https://news.ycombinator.com/rss",
}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_create_feed_attaches_it_to_the_current_user_and_its_engine(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    response = await client.post("/feeds", headers=headers, json=FEED_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "miniflux"
    assert body["title"] == "Hacker News"

    list_response = await client.get("/feeds", headers=headers)
    assert len(list_response.json()) == 1


async def test_delete_feed_removes_it(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    create_response = await client.post("/feeds", headers=headers, json=FEED_PAYLOAD)
    feed_id = create_response.json()["id"]

    delete_response = await client.delete(f"/feeds/{feed_id}", headers=headers)
    assert delete_response.status_code == 204

    list_response = await client.get("/feeds", headers=headers)
    assert list_response.json() == []


async def test_delete_feed_of_another_user_is_rejected(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    create_response = await client.post("/feeds", headers=headers, json=FEED_PAYLOAD)
    feed_id = create_response.json()["id"]

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        instance = (await session.scalars(select(Instance))).one()
        other_user = User(
            instance_id=instance.id,
            email="member@example.com",
            username="member",
            password_hash=None,
        )
        session.add(other_user)
        await session.commit()
        other_user_id = other_user.id

    other_headers = {"Authorization": f"Bearer {create_access_token(other_user_id)}"}
    delete_response = await client.delete(f"/feeds/{feed_id}", headers=other_headers)
    assert delete_response.status_code in (403, 404)

    list_response = await client.get("/feeds", headers=headers)
    assert len(list_response.json()) == 1


async def test_delete_an_unknown_feed_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    response = await client.delete(
        "/feeds/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404
