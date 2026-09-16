"""Picking up the feeds a long-running Miniflux already polls.

A reader grafting Lumia onto their own instance has feeds there and no `feeds` row for any of
them. They must be able to see that list, with the category they were filed under, and subscribe
to a chosen few without Miniflux being asked for a single new feed.
"""

from collections.abc import AsyncIterator, Callable

import httpx
import pytest

from api.main import app
from worker.technical.connectors.miniflux_client import get_miniflux_transport

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}

INSTANCE_FEEDS = [
    {
        "id": 42,
        "title": "LWN.net",
        "feed_url": "https://lwn.net/headlines/rss",
        "category": {"id": 3, "title": "Linux"},
    },
    {
        "id": 43,
        "title": "Hacker News",
        "feed_url": "https://hnrss.org/frontpage",
        "category": {"id": 1, "title": "All"},
    },
    {"id": 44, "title": "", "feed_url": "https://untitled.test/rss"},
]


def _miniflux_handler(request: httpx.Request) -> httpx.Response:
    if request.method == "GET" and request.url.path == "/v1/feeds":
        return httpx.Response(200, json=INSTANCE_FEEDS)
    raise AssertionError(f"unexpected request {request.method} {request.url}")


def _client_talking_to(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.AsyncClient:
    app.dependency_overrides[get_miniflux_transport] = lambda: httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    async with _client_talking_to(_miniflux_handler) as async_client:
        yield async_client
    app.dependency_overrides.pop(get_miniflux_transport, None)


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_the_instance_feeds_are_listed_with_their_category(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)

    response = await client.get("/feeds/instance", headers=headers)

    assert response.status_code == 200
    assert response.json()[:2] == [
        {
            "external_feed_id": "42",
            "title": "LWN.net",
            "url": "https://lwn.net/headlines/rss",
            "category": "Linux",
        },
        {
            "external_feed_id": "43",
            "title": "Hacker News",
            "url": "https://hnrss.org/frontpage",
            "category": "All",
        },
    ]


async def test_a_feed_filed_nowhere_in_miniflux_has_no_category(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)

    response = await client.get("/feeds/instance", headers=headers)

    uncategorised = next(item for item in response.json() if item["external_feed_id"] == "44")
    assert uncategorised["category"] is None
    # Miniflux lets a feed carry no title; the URL is the only name left to show.
    assert uncategorised["title"] == "https://untitled.test/rss"


async def test_attaching_creates_the_rows_with_the_existing_miniflux_ids(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/feeds/instance/attach", headers=headers, json={"external_feed_ids": ["42"]}
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["external_feed_id"] == "42"
    assert body[0]["url"] == "https://lwn.net/headlines/rss"
    assert body[0]["source_type"] == "miniflux"


async def test_attaching_files_the_feed_into_a_folder_named_after_the_category(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)

    attached = await client.post(
        "/feeds/instance/attach", headers=headers, json={"external_feed_ids": ["42"]}
    )

    folders = (await client.get("/folders", headers=headers)).json()
    linux = next(folder for folder in folders if folder["name"] == "Linux")
    assert attached.json()[0]["folder_id"] == linux["id"]


async def test_only_the_ticked_feeds_are_attached(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    await client.post("/feeds/instance/attach", headers=headers, json={"external_feed_ids": ["43"]})

    subscribed = (await client.get("/feeds", headers=headers)).json()
    assert [feed["external_feed_id"] for feed in subscribed] == ["43"]


async def test_attaching_never_asks_miniflux_for_a_new_feed(db_schema: None) -> None:
    """The whole point: the instance keeps exactly the feeds it had."""
    written: list[str] = []

    def recording(request: httpx.Request) -> httpx.Response:
        if request.method != "GET":
            written.append(f"{request.method} {request.url.path}")
        return _miniflux_handler(request)

    async with _client_talking_to(recording) as client:
        headers = await _headers(client)
        await client.post(
            "/feeds/instance/attach", headers=headers, json={"external_feed_ids": ["42", "43"]}
        )
    app.dependency_overrides.pop(get_miniflux_transport, None)

    assert written == []


async def test_a_feed_already_subscribed_drops_off_the_list(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await client.post("/feeds/instance/attach", headers=headers, json={"external_feed_ids": ["42"]})

    response = await client.get("/feeds/instance", headers=headers)

    assert [item["external_feed_id"] for item in response.json()] == ["43", "44"]


async def test_attaching_twice_does_not_duplicate_the_subscription(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await client.post("/feeds/instance/attach", headers=headers, json={"external_feed_ids": ["42"]})

    second = await client.post(
        "/feeds/instance/attach", headers=headers, json={"external_feed_ids": ["42"]}
    )

    assert second.json() == []
    subscribed = (await client.get("/feeds", headers=headers)).json()
    assert len(subscribed) == 1


async def test_an_id_the_instance_no_longer_carries_is_skipped(
    client: httpx.AsyncClient,
) -> None:
    """The ticked list is a snapshot; a feed deleted in Miniflux meanwhile must not sink the batch."""
    headers = await _headers(client)

    response = await client.post(
        "/feeds/instance/attach", headers=headers, json={"external_feed_ids": ["999", "42"]}
    )

    assert [feed["external_feed_id"] for feed in response.json()] == ["42"]


async def test_an_unreachable_miniflux_answers_502(db_schema: None) -> None:
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("miniflux is down")

    async with _client_talking_to(unreachable) as client:
        headers = await _headers(client)
        response = await client.get("/feeds/instance", headers=headers)
    app.dependency_overrides.pop(get_miniflux_transport, None)

    assert response.status_code == 502


async def test_listing_the_instance_feeds_requires_an_account(client: httpx.AsyncClient) -> None:
    response = await client.get("/feeds/instance")

    assert response.status_code == 401
