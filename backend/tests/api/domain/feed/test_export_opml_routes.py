from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.user.models import Instance, User
from api.main import app
from api.technical.auth.jwt import create_access_token
from api.technical.net.url_guard import get_url_resolver
from config.database import get_engine
from worker.technical.connectors.miniflux_client import get_miniflux_transport

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}

HN_FEED = {
    "source_type": "miniflux",
    "external_feed_id": "1",
    "title": "Hacker News",
    "url": "https://hnrss.org/frontpage",
}

LOBSTERS_FEED = {
    "source_type": "miniflux",
    "external_feed_id": "2",
    "title": "Lobsters",
    "url": "https://lobste.rs/rss",
}


def _resolve_to_the_public_internet(host: str) -> list[str]:
    return ["93.184.216.34"]


def _miniflux_handler(request: httpx.Request) -> httpx.Response:
    if request.method == "GET" and request.url.path == "/v1/feeds":
        return httpx.Response(200, json=[])
    if request.method == "GET" and request.url.path == "/v1/categories":
        return httpx.Response(200, json=[])
    if request.method == "POST" and request.url.path == "/v1/categories":
        return httpx.Response(201, json={"id": 1, "title": "News"})
    if request.method == "POST" and request.url.path == "/v1/feeds":
        return httpx.Response(201, json={"feed_id": 7})
    raise AssertionError(f"unexpected request {request.method} {request.url}")


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    app.dependency_overrides[get_miniflux_transport] = lambda: httpx.MockTransport(
        _miniflux_handler
    )
    app.dependency_overrides[get_url_resolver] = lambda: _resolve_to_the_public_internet
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.pop(get_miniflux_transport, None)
    app.dependency_overrides.pop(get_url_resolver, None)


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _other_user_headers(email: str, username: str) -> dict[str, str]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        instance = (await session.scalars(select(Instance))).one()
        other_user = User(
            instance_id=instance.id,
            email=email,
            username=username,
            password_hash=None,
        )
        session.add(other_user)
        await session.commit()
        other_user_id = other_user.id
    return {"Authorization": f"Bearer {create_access_token(other_user_id)}"}


async def test_export_opml_returns_a_downloadable_document(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await client.post("/feeds", headers=headers, json=HN_FEED)

    response = await client.get("/feeds/export-opml", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/x-opml")
    assert "attachment" in response.headers["content-disposition"]
    assert b"hnrss.org/frontpage" in response.content


async def test_export_opml_without_a_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.get("/feeds/export-opml")
    assert response.status_code == 401


async def test_export_opml_only_contains_the_caller_own_feeds(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await client.post("/feeds", headers=headers, json=HN_FEED)

    other_headers = await _other_user_headers("member@example.com", "member")
    await client.post("/feeds", headers=other_headers, json=LOBSTERS_FEED)

    response = await client.get("/feeds/export-opml", headers=headers)

    assert b"hnrss.org/frontpage" in response.content
    assert b"lobste.rs" not in response.content


async def test_export_then_reimport_into_a_second_account_preserves_feeds_and_folders(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    folder_response = await client.post("/folders", headers=headers, json={"name": "Tech news"})
    folder_id = folder_response.json()["id"]
    await client.post("/feeds", headers=headers, json={**HN_FEED, "folder_id": folder_id})
    await client.post("/feeds", headers=headers, json=LOBSTERS_FEED)

    export_response = await client.get("/feeds/export-opml", headers=headers)
    assert export_response.status_code == 200

    other_headers = await _other_user_headers("member@example.com", "member")
    import_response = await client.post(
        "/feeds/import-opml",
        headers=other_headers,
        files={"file": ("subs.opml", export_response.content, "text/x-opml")},
    )
    assert import_response.status_code == 200

    feeds_response = await client.get("/feeds", headers=other_headers)
    imported_feeds = feeds_response.json()
    assert {feed["url"] for feed in imported_feeds} == {HN_FEED["url"], LOBSTERS_FEED["url"]}

    folders_response = await client.get("/folders", headers=other_headers)
    imported_folders = folders_response.json()
    assert [folder["name"] for folder in imported_folders] == ["Tech news"]

    filed_feed = next(feed for feed in imported_feeds if feed["url"] == HN_FEED["url"])
    assert filed_feed["folder_id"] == imported_folders[0]["id"]
    unfiled_feed = next(feed for feed in imported_feeds if feed["url"] == LOBSTERS_FEED["url"])
    assert unfiled_feed["folder_id"] is None
