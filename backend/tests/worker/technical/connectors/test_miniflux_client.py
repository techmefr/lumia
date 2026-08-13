import httpx
import pytest

from worker.technical.connectors import miniflux_client
from worker.technical.connectors.miniflux_client import (
    MinifluxApiError,
    create_category,
    create_feed,
    get_feed,
    list_categories,
)


def test_miniflux_client_allows_time_for_the_synchronous_feed_fetch() -> None:
    client = miniflux_client._client(None)
    # Registering a feed makes Miniflux fetch and parse it live before responding;
    # httpx's 5s default routinely isn't enough for that first fetch.
    read_timeout = client.timeout.read
    assert read_timeout is not None
    assert read_timeout >= 15.0


async def test_create_category_returns_the_category_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/categories"
        assert request.headers["authorization"].startswith("Basic ")
        return httpx.Response(201, json={"id": 42, "title": "Tech"})

    category = await create_category("Tech", transport=httpx.MockTransport(handler))
    assert category.category_id == 42


async def test_create_feed_returns_the_feed_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/feeds"
        return httpx.Response(201, json={"feed_id": 7})

    feed = await create_feed(
        "https://example.com/feed.xml",
        category_id=42,
        transport=httpx.MockTransport(handler),
    )
    assert feed.feed_id == 7


async def test_create_feed_omits_category_id_when_not_given() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "category_id" not in request.content.decode()
        return httpx.Response(201, json={"feed_id": 9})

    feed = await create_feed(
        "https://example.com/feed.xml", transport=httpx.MockTransport(handler)
    )
    assert feed.feed_id == 9


async def test_list_categories_returns_the_id_and_title_of_each() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/categories"
        return httpx.Response(200, json=[{"id": 1, "title": "All"}, {"id": 2, "title": "Tech"}])

    categories = await list_categories(transport=httpx.MockTransport(handler))
    assert {(category.category_id, category.title) for category in categories} == {
        (1, "All"),
        (2, "Tech"),
    }


async def test_create_feed_raises_on_an_error_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    with pytest.raises(MinifluxApiError):
        await create_feed(
            "https://example.com/feed.xml",
            category_id=42,
            transport=httpx.MockTransport(handler),
        )


async def test_get_feed_returns_the_id_and_title() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/feeds/7"
        return httpx.Response(200, json={"id": 7, "title": "Hacker News"})

    feed = await get_feed(7, transport=httpx.MockTransport(handler))
    assert feed.feed_id == 7
    assert feed.title == "Hacker News"


async def test_get_feed_raises_on_an_error_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    with pytest.raises(MinifluxApiError):
        await get_feed(7, transport=httpx.MockTransport(handler))
