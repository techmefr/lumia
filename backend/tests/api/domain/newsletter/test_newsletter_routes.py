from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.feed.models import Feed, SourceType
from api.domain.newsletter.models import NewsletterInbox
from api.domain.newsletter.routes import MAX_INBOUND_BYTES
from api.main import app
from config.database import get_engine
from tests.fake_arq_pool import FakeArqPool
from worker.technical.connectors.base import RawArticle
from worker.technical.queue import get_arq_pool

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}
MESSAGE = {
    "sender": "Le Quotidien <hello@quotidien.example>",
    "subject": "Issue 12",
    "html": "<p>Bonjour</p><script>alert(1)</script><a href='javascript:alert(2)'>x</a>",
    "message_id": "<abc@quotidien.example>",
    "date": "2026-10-20T07:00:00Z",
    "attachments": [{"filename": "big.pdf", "content": "AAAA"}],
}


@pytest.fixture
def pool() -> FakeArqPool:
    return FakeArqPool()


@pytest.fixture
async def client(db_schema: None, pool: FakeArqPool) -> AsyncIterator[httpx.AsyncClient]:
    app.dependency_overrides[get_arq_pool] = lambda: pool
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _open_inbox(client: httpx.AsyncClient, headers: dict[str, str]) -> str:
    response = await client.post("/newsletters/inbox", headers=headers)
    assert response.status_code == 201
    return str(response.json()["token"])


def _enqueued_article(pool: FakeArqPool) -> RawArticle:
    function, args, _ = pool.enqueued[-1]
    assert function == "enrich_article"
    article: Any = args[0]
    assert isinstance(article, RawArticle)
    return article


async def test_a_reader_without_an_inbox_is_reported_inactive(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.get("/newsletters/inbox", headers=headers)

    assert response.json() == {"active": False, "created_at": None}


async def test_the_inbox_routes_require_a_session(client: httpx.AsyncClient) -> None:
    assert (await client.get("/newsletters/inbox")).status_code == 401
    assert (await client.post("/newsletters/inbox")).status_code == 401
    assert (await client.delete("/newsletters/inbox")).status_code == 401


async def test_creating_an_inbox_shows_the_token_once_and_stores_only_its_hash(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)

    token = await _open_inbox(client, headers)

    status = (await client.get("/newsletters/inbox", headers=headers)).json()
    assert status["active"] is True
    assert "token" not in status
    async with async_sessionmaker(get_engine())() as session:
        stored = (await session.scalars(select(NewsletterInbox))).one()
    assert token not in stored.token_hash


async def test_a_delivery_is_queued_as_a_sanitised_article_on_the_readers_feed(
    client: httpx.AsyncClient, pool: FakeArqPool
) -> None:
    headers = await _headers(client)
    token = await _open_inbox(client, headers)

    response = await client.post(f"/inbound/newsletters/{token}", json=MESSAGE)

    assert response.status_code == 202
    article = _enqueued_article(pool)
    assert article.title == "Issue 12"
    assert article.author_name == "Le Quotidien"
    assert "Bonjour" in article.content
    assert "script" not in article.content
    assert "javascript:" not in article.content
    assert article.source_type == "manual"
    assert article.url.startswith("urn:lumia:newsletter:")
    async with async_sessionmaker(get_engine())() as session:
        feed = (await session.scalars(select(Feed).where(Feed.title == "Newsletters"))).one()
    assert feed.source_type is SourceType.MANUAL
    assert feed.external_feed_id == article.feed_external_id


async def test_redelivering_the_same_message_yields_the_same_entry_and_one_feed(
    client: httpx.AsyncClient, pool: FakeArqPool
) -> None:
    headers = await _headers(client)
    token = await _open_inbox(client, headers)

    await client.post(f"/inbound/newsletters/{token}", json=MESSAGE)
    first = _enqueued_article(pool)
    await client.post(f"/inbound/newsletters/{token}", json=MESSAGE)
    second = _enqueued_article(pool)

    assert first.external_entry_id == second.external_entry_id
    assert first.url == second.url
    async with async_sessionmaker(get_engine())() as session:
        feeds = await session.scalar(
            select(func.count()).select_from(Feed).where(Feed.title == "Newsletters")
        )
    assert feeds == 1


async def test_a_text_only_mail_is_escaped_into_paragraphs(
    client: httpx.AsyncClient, pool: FakeArqPool
) -> None:
    headers = await _headers(client)
    token = await _open_inbox(client, headers)

    await client.post(
        f"/inbound/newsletters/{token}",
        json={"sender": "a@b.example", "text": "Un <b>deux</b>\n\nTrois"},
    )

    article = _enqueued_article(pool)
    assert article.content == "<p>Un &lt;b&gt;deux&lt;/b&gt;</p><p>Trois</p>"
    assert article.title == "(no subject)"
    assert article.author_name == "a@b.example"


async def test_a_mail_without_a_body_is_refused(
    client: httpx.AsyncClient, pool: FakeArqPool
) -> None:
    headers = await _headers(client)
    token = await _open_inbox(client, headers)

    response = await client.post(
        f"/inbound/newsletters/{token}", json={"sender": "a@b.example", "html": "  "}
    )

    assert response.status_code == 422
    assert pool.enqueued == []


async def test_a_malformed_payload_is_refused(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    token = await _open_inbox(client, headers)

    response = await client.post(f"/inbound/newsletters/{token}", content=b"not json")

    assert response.status_code == 422


async def test_an_oversized_delivery_is_refused_before_it_is_parsed(
    client: httpx.AsyncClient, pool: FakeArqPool
) -> None:
    headers = await _headers(client)
    token = await _open_inbox(client, headers)
    huge = {"sender": "a@b.example", "html": "x" * (MAX_INBOUND_BYTES + 1)}

    response = await client.post(f"/inbound/newsletters/{token}", json=huge)

    assert response.status_code == 413
    assert pool.enqueued == []


async def test_an_oversized_body_without_a_declared_length_is_refused_too(
    client: httpx.AsyncClient, pool: FakeArqPool
) -> None:
    headers = await _headers(client)
    token = await _open_inbox(client, headers)

    async def chunks() -> AsyncIterator[bytes]:
        for _ in range(MAX_INBOUND_BYTES // 65536 + 2):
            yield b"x" * 65536

    response = await client.post(f"/inbound/newsletters/{token}", content=chunks())

    assert response.status_code == 413
    assert pool.enqueued == []


async def test_an_unknown_token_is_not_found(client: httpx.AsyncClient, pool: FakeArqPool) -> None:
    await _headers(client)

    response = await client.post(f"/inbound/newsletters/{'x' * 43}", json=MESSAGE)

    assert response.status_code == 404
    assert pool.enqueued == []


async def test_rotating_the_inbox_retires_the_previous_address(
    client: httpx.AsyncClient, pool: FakeArqPool
) -> None:
    headers = await _headers(client)
    old = await _open_inbox(client, headers)
    new = await _open_inbox(client, headers)

    assert (await client.post(f"/inbound/newsletters/{old}", json=MESSAGE)).status_code == 404
    assert (await client.post(f"/inbound/newsletters/{new}", json=MESSAGE)).status_code == 202


async def test_revoking_the_inbox_closes_the_address(
    client: httpx.AsyncClient, pool: FakeArqPool
) -> None:
    headers = await _headers(client)
    token = await _open_inbox(client, headers)

    assert (await client.delete("/newsletters/inbox", headers=headers)).status_code == 204

    assert (await client.post(f"/inbound/newsletters/{token}", json=MESSAGE)).status_code == 404
    status = (await client.get("/newsletters/inbox", headers=headers)).json()
    assert status["active"] is False


async def test_deleting_the_account_removes_its_inbox(client: httpx.AsyncClient) -> None:
    from api.domain.user.account_service import delete_account
    from api.domain.user.models import User

    headers = await _headers(client)
    await _open_inbox(client, headers)
    # Deleting the only admin is refused, so a second account is needed to go through the path.
    sessions = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with sessions() as session:
        admin = (await session.scalars(select(User))).one()
        reader = User(
            instance_id=admin.instance_id,
            email="reader@example.com",
            username="reader",
            password_hash="x",
        )
        session.add(reader)
        await session.commit()
        session.add(NewsletterInbox(user_id=reader.id, token_hash="h"))
        await session.commit()
        await delete_account(session, reader.id)
        remaining = list((await session.scalars(select(NewsletterInbox))).all())
    assert [inbox.user_id for inbox in remaining] == [admin.id]
