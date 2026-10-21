from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import User
from api.domain.webhook.models import DeliveryStatus, OutboundWebhook, WebhookDelivery
from api.domain.webhook.publisher import QUEUE_UNAVAILABLE, EventPublisher, get_event_publisher
from api.domain.webhook.service import MAX_WEBHOOKS_PER_USER
from api.main import app
from api.technical.auth.jwt import create_access_token
from api.technical.crypto.secret_box import decrypt_secret
from api.technical.net.url_guard import get_url_resolver
from config.database import get_engine
from tests.fake_arq_pool import FakeArqPool

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}
HOOK = {"url": "https://hooks.example.com/lumia", "events": ["article.saved"]}


@pytest.fixture
def pool() -> FakeArqPool:
    return FakeArqPool()


@pytest.fixture
async def client(db_schema: None, pool: FakeArqPool) -> AsyncIterator[httpx.AsyncClient]:
    async def pool_factory() -> FakeArqPool:
        return pool

    app.dependency_overrides[get_url_resolver] = lambda: lambda host: ["93.184.216.34"]
    app.dependency_overrides[get_event_publisher] = lambda: EventPublisher(pool_factory)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


def _factory() -> async_sessionmaker:  # type: ignore[type-arg]
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _stranger_headers() -> dict[str, str]:
    async with _factory()() as session:
        owner = (await session.scalars(select(User).order_by(User.created_at))).first()
        assert owner is not None
        user = User(instance_id=owner.instance_id, email="other@example.com", username="other")
        session.add(user)
        await session.commit()
        return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def _seed_articles(count: int) -> list[str]:
    async with _factory()() as session:
        user = (await session.scalars(select(User).order_by(User.created_at))).first()
        assert user is not None
        feed = Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="1",
            title="Feed",
            url="https://example.com/feed",
        )
        session.add(feed)
        await session.flush()
        articles = [
            Article(
                feed_id=feed.id,
                external_entry_id=str(index),
                title=f"Article {index}",
                url=f"https://example.com/a/{index}",
                content="Content",
                published_at=datetime(2026, 8, 12, tzinfo=UTC),
            )
            for index in range(count)
        ]
        session.add_all(articles)
        await session.commit()
        return [str(article.id) for article in articles]


async def _create(
    client: httpx.AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    response = await client.post("/outbound-webhooks", json={**HOOK, **overrides}, headers=headers)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def _deliveries() -> list[WebhookDelivery]:
    async with _factory()() as session:
        return list(await session.scalars(select(WebhookDelivery)))


async def test_creating_a_webhook_returns_its_secret_once_and_stores_it_encrypted(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)

    created = await _create(client, headers)

    listed = (await client.get("/outbound-webhooks", headers=headers)).json()
    assert [item["id"] for item in listed] == [created["id"]]
    assert "secret" not in listed[0]
    async with _factory()() as session:
        stored = (await session.scalars(select(OutboundWebhook))).one()
    assert stored.secret_encrypted != created["secret"]
    assert decrypt_secret(stored.secret_encrypted) == created["secret"]


async def test_an_address_resolving_to_a_private_network_is_refused(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    app.dependency_overrides[get_url_resolver] = lambda: lambda host: ["10.0.0.5"]

    response = await client.post("/outbound-webhooks", json=HOOK, headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"] == "webhook_url_blocked"
    assert (await client.get("/outbound-webhooks", headers=headers)).json() == []


async def test_a_non_http_address_is_refused(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/outbound-webhooks", json={**HOOK, "url": "file:///etc/passwd"}, headers=headers
    )

    assert response.status_code == 422


@pytest.mark.parametrize("events", [[], ["article.deleted"]])
async def test_an_empty_or_unknown_event_list_is_refused(
    client: httpx.AsyncClient, events: list[str]
) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/outbound-webhooks", json={**HOOK, "events": events}, headers=headers
    )

    assert response.status_code == 422


async def test_the_number_of_webhooks_per_reader_is_capped(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    for _ in range(MAX_WEBHOOKS_PER_USER):
        await _create(client, headers)

    response = await client.post("/outbound-webhooks", json=HOOK, headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "webhook_limit_reached"


async def test_a_reader_cannot_see_change_or_remove_the_webhook_of_another(
    client: httpx.AsyncClient,
) -> None:
    owner = await _headers(client)
    stranger = await _stranger_headers()
    created = await _create(client, owner)
    path = f"/outbound-webhooks/{created['id']}"

    assert (await client.get("/outbound-webhooks", headers=stranger)).json() == []
    assert (await client.patch(path, json={"active": False}, headers=stranger)).status_code == 404
    assert (await client.delete(path, headers=stranger)).status_code == 404
    assert (await client.get(f"{path}/deliveries", headers=stranger)).status_code == 404
    still = (await client.get("/outbound-webhooks", headers=owner)).json()
    assert still[0]["active"] is True


async def test_a_webhook_can_be_paused_retargeted_and_removed(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    created = await _create(client, headers)
    path = f"/outbound-webhooks/{created['id']}"

    patched = await client.patch(
        path,
        json={"active": False, "events": ["article.favorited", "article.favorited"]},
        headers=headers,
    )

    assert patched.json()["active"] is False
    assert patched.json()["events"] == ["article.favorited"]
    assert (await client.delete(path, headers=headers)).status_code == 204
    assert (await client.get("/outbound-webhooks", headers=headers)).json() == []


async def test_a_new_address_goes_through_the_guard_again(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    created = await _create(client, headers)
    app.dependency_overrides[get_url_resolver] = lambda: lambda host: ["127.0.0.1"]

    response = await client.patch(
        f"/outbound-webhooks/{created['id']}",
        json={"url": "https://elsewhere.example.com/x"},
        headers=headers,
    )

    assert response.status_code == 422


async def test_saving_an_article_queues_a_signed_delivery_for_a_listening_webhook(
    client: httpx.AsyncClient, pool: FakeArqPool
) -> None:
    headers = await _headers(client)
    created = await _create(client, headers)
    (article_id,) = await _seed_articles(1)

    response = await client.post(
        f"/articles/{article_id}/feedback", json={"saved": True}, headers=headers
    )

    assert response.status_code == 204
    (delivery,) = await _deliveries()
    assert delivery.event == "article.saved"
    assert delivery.status is DeliveryStatus.PENDING
    assert str(delivery.webhook_id) == created["id"]
    assert delivery.payload["article"] == {
        "id": article_id,
        "title": "Article 0",
        "url": "https://example.com/a/0",
    }
    assert pool.enqueued == [("deliver_webhook", (str(delivery.id),), {})]


async def test_repeating_a_state_the_reader_already_had_is_not_an_event(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await _create(client, headers)
    (article_id,) = await _seed_articles(1)
    for _ in range(2):
        await client.post(f"/articles/{article_id}/feedback", json={"saved": True}, headers=headers)

    assert len(await _deliveries()) == 1


async def test_an_event_nobody_listens_for_creates_no_delivery(
    client: httpx.AsyncClient, pool: FakeArqPool
) -> None:
    headers = await _headers(client)
    await _create(client, headers, events=["article.favorited"])
    (article_id,) = await _seed_articles(1)

    await client.post(f"/articles/{article_id}/feedback", json={"saved": True}, headers=headers)

    assert await _deliveries() == []
    assert pool.enqueued == []


async def test_a_paused_webhook_receives_nothing(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    created = await _create(client, headers)
    await client.patch(
        f"/outbound-webhooks/{created['id']}", json={"active": False}, headers=headers
    )
    (article_id,) = await _seed_articles(1)

    await client.post(f"/articles/{article_id}/feedback", json={"saved": True}, headers=headers)

    assert await _deliveries() == []


async def test_favoriting_one_article_emits_the_favorited_event(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _create(client, headers, events=["article.favorited"])
    (article_id,) = await _seed_articles(1)

    await client.post(f"/articles/{article_id}/feedback", json={"favorite": True}, headers=headers)

    assert [delivery.event for delivery in await _deliveries()] == ["article.favorited"]


async def test_bulk_favoriting_emits_one_delivery_per_article_that_changed(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await _create(client, headers, events=["article.favorited"])
    first, second = await _seed_articles(2)
    await client.post(f"/articles/{first}/feedback", json={"favorite": True}, headers=headers)
    before = len(await _deliveries())

    await client.post(
        "/articles/bulk-feedback",
        json={"article_ids": [first, second], "axis": "favorite", "value": True},
        headers=headers,
    )

    deliveries = (await _deliveries())[before:]
    assert [delivery.payload["article"]["id"] for delivery in deliveries] == [second]  # type: ignore[index]


async def test_removing_a_flag_in_bulk_emits_nothing(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _create(client, headers, events=["article.saved"])
    (article_id,) = await _seed_articles(1)
    await client.post(f"/articles/{article_id}/feedback", json={"saved": True}, headers=headers)
    before = len(await _deliveries())

    await client.post(
        "/articles/bulk-feedback",
        json={"article_ids": [article_id], "axis": "saved", "value": False},
        headers=headers,
    )

    assert len(await _deliveries()) == before


async def test_adding_to_a_playlist_names_the_playlist_and_ignores_a_duplicate(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await _create(client, headers, events=["playlist.article_added"])
    (article_id,) = await _seed_articles(1)
    playlist = (await client.post("/playlists", json={"name": "Weekend"}, headers=headers)).json()
    path = f"/playlists/{playlist['id']}/items"

    await client.post(path, json={"article_id": article_id}, headers=headers)
    await client.post(path, json={"article_id": article_id}, headers=headers)

    (delivery,) = await _deliveries()
    assert delivery.payload["playlist"] == {"id": playlist["id"], "name": "Weekend"}


async def test_bulk_adding_to_a_playlist_emits_one_delivery_per_added_article(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await _create(client, headers, events=["playlist.article_added"])
    ids = await _seed_articles(2)
    playlist = (await client.post("/playlists", json={"name": "Batch"}, headers=headers)).json()

    await client.post(
        f"/playlists/{playlist['id']}/items/bulk",
        json={"article_ids": ids, "present": True},
        headers=headers,
    )

    assert len(await _deliveries()) == 2


async def test_a_dead_queue_marks_the_delivery_failed_and_the_save_still_succeeds(
    db_schema: None,
) -> None:
    async def broken_pool() -> FakeArqPool:
        raise ConnectionError("redis is gone")

    app.dependency_overrides[get_event_publisher] = lambda: EventPublisher(broken_pool)
    app.dependency_overrides[get_url_resolver] = lambda: lambda host: ["93.184.216.34"]
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _headers(client)
        await _create(client, headers)
        (article_id,) = await _seed_articles(1)

        response = await client.post(
            f"/articles/{article_id}/feedback", json={"saved": True}, headers=headers
        )

    app.dependency_overrides.clear()
    assert response.status_code == 204
    (delivery,) = await _deliveries()
    assert delivery.status is DeliveryStatus.FAILED
    assert delivery.last_error == QUEUE_UNAVAILABLE


async def test_the_delivery_history_shows_the_outcome_of_each_event(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    created = await _create(client, headers)
    (article_id,) = await _seed_articles(1)
    await client.post(f"/articles/{article_id}/feedback", json={"saved": True}, headers=headers)
    async with _factory()() as session:
        delivery = (await session.scalars(select(WebhookDelivery))).one()
        delivery.status = DeliveryStatus.FAILED
        delivery.attempts = 5
        delivery.last_error = "HTTP 503"
        delivery.last_status_code = 503
        await session.commit()
        delivery_id = delivery.id

    history = (
        await client.get(f"/outbound-webhooks/{created['id']}/deliveries", headers=headers)
    ).json()

    assert history[0]["id"] == str(delivery_id)
    assert history[0]["status"] == "failed"
    assert history[0]["attempts"] == 5
    assert history[0]["last_error"] == "HTTP 503"
    assert UUID(history[0]["id"]) == delivery_id
