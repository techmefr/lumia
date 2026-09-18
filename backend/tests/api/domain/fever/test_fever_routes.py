import hashlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, Folder, SourceType
from api.domain.recommendation.models import UserArticleFeedback
from api.domain.user.models import Instance, User
from api.main import app
from config.database import get_engine

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


def _wire_api_key(email: str, token: str) -> str:
    """What a real Fever client sends: it never sees the token as such, only the digest it
    computes itself from the email and the token pasted in as the client's "password" field."""
    return hashlib.md5(f"{email}:{token}".encode()).hexdigest()


async def test_wrong_api_key_is_rejected_with_auth_zero(client: httpx.AsyncClient) -> None:
    await _headers(client)

    response = await client.post("/fever/", params={"api": ""}, data={"api_key": "not-a-real-key"})

    assert response.status_code == 200
    assert response.json() == {"api_version": 3, "auth": 0}


async def test_issued_api_key_authenticates_the_fever_request(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    key_response = await client.post("/fever/api-key", headers=headers)
    assert key_response.status_code == 200
    body = key_response.json()
    api_key = _wire_api_key(body["email"], body["api_key"])

    response = await client.post("/fever/", params={"api": ""}, data={"api_key": api_key})

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == 3
    assert body["auth"] == 1


async def test_api_key_status_reflects_issuance_and_revocation(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    before = await client.get("/fever/api-key", headers=headers)
    assert before.json() == {"configured": False}

    await client.post("/fever/api-key", headers=headers)
    after = await client.get("/fever/api-key", headers=headers)
    assert after.json() == {"configured": True}

    delete_response = await client.delete("/fever/api-key", headers=headers)
    assert delete_response.status_code == 204
    revoked = await client.get("/fever/api-key", headers=headers)
    assert revoked.json() == {"configured": False}


async def test_reissuing_the_api_key_invalidates_the_previous_one(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    first_body = (await client.post("/fever/api-key", headers=headers)).json()
    second_body = (await client.post("/fever/api-key", headers=headers)).json()
    first = _wire_api_key(first_body["email"], first_body["api_key"])
    second = _wire_api_key(second_body["email"], second_body["api_key"])

    stale_response = await client.post("/fever/", params={"api": ""}, data={"api_key": first})
    fresh_response = await client.post("/fever/", params={"api": ""}, data={"api_key": second})

    assert stale_response.json()["auth"] == 0
    assert fresh_response.json()["auth"] == 1


async def _seed(headers: dict[str, str], client: httpx.AsyncClient) -> tuple[str, dict[str, str]]:
    key_body = (await client.post("/fever/api-key", headers=headers)).json()
    api_key = _wire_api_key(key_body["email"], key_body["api_key"])

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        folder = Folder(user_id=user.id, name="Tech")
        session.add(folder)
        await session.flush()
        feed = Feed(
            user_id=user.id,
            folder_id=folder.id,
            source_type=SourceType.MANUAL,
            external_feed_id="ext-1",
            title="A Feed",
            url="https://example.test/feed.xml",
        )
        session.add(feed)
        await session.flush()
        article = Article(
            feed_id=feed.id,
            external_entry_id="entry-1",
            title="An article",
            url="https://example.test/a",
            content="<p>hello</p>",
            published_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        session.add(article)
        await session.commit()
    return api_key, headers


async def test_groups_lists_folders_and_their_feed_membership(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    api_key, _ = await _seed(headers, client)

    response = await client.post(
        "/fever/", params={"api": "", "groups": ""}, data={"api_key": api_key}
    )

    body = response.json()
    assert body["groups"] == [{"id": 1, "title": "Tech"}]
    assert body["feeds_groups"] == [{"group_id": 1, "feed_ids": "1"}]


async def test_feeds_lists_the_users_feeds_with_fever_field_names(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    api_key, _ = await _seed(headers, client)

    response = await client.post(
        "/fever/", params={"api": "", "feeds": ""}, data={"api_key": api_key}
    )

    body = response.json()
    assert len(body["feeds"]) == 1
    feed = body["feeds"][0]
    assert feed["id"] == 1
    assert feed["title"] == "A Feed"
    assert feed["url"] == "https://example.test/feed.xml"
    assert feed["is_spark"] == 0


async def test_items_returns_articles_with_fever_field_names(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    api_key, _ = await _seed(headers, client)

    response = await client.post(
        "/fever/", params={"api": "", "items": ""}, data={"api_key": api_key}
    )

    body = response.json()
    assert body["total_items"] == 1
    item = body["items"][0]
    assert item["id"] == 1
    assert item["feed_id"] == 1
    assert item["title"] == "An article"
    assert item["html"] == "<p>hello</p>"
    assert item["is_read"] == 0
    assert item["is_saved"] == 0


async def test_unread_item_ids_excludes_articles_marked_read(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    api_key, _ = await _seed(headers, client)

    unread_before = await client.post(
        "/fever/", params={"api": "", "unread_item_ids": ""}, data={"api_key": api_key}
    )
    assert unread_before.json()["unread_item_ids"] == "1"

    await client.post(
        "/fever/",
        params={"api": ""},
        data={"api_key": api_key, "mark": "item", "as": "read", "id": "1"},
    )

    unread_after = await client.post(
        "/fever/", params={"api": "", "unread_item_ids": ""}, data={"api_key": api_key}
    )
    assert unread_after.json()["unread_item_ids"] == ""


async def test_marking_an_item_read_via_fever_is_visible_through_the_normal_feedback_axis(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    api_key, _ = await _seed(headers, client)

    await client.post(
        "/fever/",
        params={"api": ""},
        data={"api_key": api_key, "mark": "item", "as": "read", "id": "1"},
    )

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        feedback = (await session.scalars(select(UserArticleFeedback))).one()
        assert feedback.read is True


async def test_marking_saved_sets_the_saved_axis(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    api_key, _ = await _seed(headers, client)

    await client.post(
        "/fever/",
        params={"api": ""},
        data={"api_key": api_key, "mark": "item", "as": "saved", "id": "1"},
    )

    response = await client.post(
        "/fever/", params={"api": "", "saved_item_ids": ""}, data={"api_key": api_key}
    )
    assert response.json()["saved_item_ids"] == "1"


async def test_fever_endpoint_never_leaks_another_users_feeds(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    api_key, _ = await _seed(headers, client)

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        instance = (await session.scalars(select(Instance))).one()
        other_user = User(
            id=uuid4(),
            instance_id=instance.id,
            email="other@example.com",
            username="other",
            password_hash=None,
        )
        session.add(other_user)
        await session.commit()

    response = await client.post(
        "/fever/", params={"api": "", "feeds": ""}, data={"api_key": api_key}
    )
    assert len(response.json()["feeds"]) == 1


def test_fever_digest_matches_the_literal_md5_the_protocol_expects() -> None:
    from api.domain.fever.key_service import _fever_digest

    digest = _fever_digest("user@example.com", "some-token")
    assert digest == hashlib.md5(b"user@example.com:some-token").hexdigest()
