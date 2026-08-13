from dataclasses import dataclass

import httpx

from config.miniflux import get_miniflux_config


class MinifluxApiError(Exception):
    pass


def get_miniflux_transport() -> httpx.AsyncBaseTransport | None:
    return None


# Registering a feed makes Miniflux synchronously fetch and parse the target URL before
# responding — httpx's 5s default is routinely too short for that first live fetch and would
# make create_feed() falsely look like it failed (feed created in Miniflux, invisible to us).
MINIFLUX_TIMEOUT = httpx.Timeout(30.0)


def _client(transport: httpx.AsyncBaseTransport | None) -> httpx.AsyncClient:
    config = get_miniflux_config()
    return httpx.AsyncClient(
        base_url=config.miniflux_base_url,
        auth=httpx.BasicAuth(config.miniflux_username, config.miniflux_password),
        transport=transport,
        timeout=MINIFLUX_TIMEOUT,
    )


@dataclass(frozen=True)
class MinifluxFeed:
    feed_id: int


@dataclass(frozen=True)
class MinifluxCategory:
    category_id: int


@dataclass(frozen=True)
class MinifluxNamedCategory:
    category_id: int
    title: str


async def list_categories(
    *, transport: httpx.AsyncBaseTransport | None = None
) -> list[MinifluxNamedCategory]:
    async with _client(transport) as client:
        response = await client.get("/v1/categories")
        if response.status_code >= 400:
            raise MinifluxApiError(response.text)
        return [
            MinifluxNamedCategory(category_id=item["id"], title=item["title"])
            for item in response.json()
        ]


async def create_category(
    title: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> MinifluxCategory:
    async with _client(transport) as client:
        response = await client.post("/v1/categories", json={"title": title})
        if response.status_code >= 400:
            raise MinifluxApiError(response.text)
        return MinifluxCategory(category_id=response.json()["id"])


async def create_feed(
    feed_url: str,
    *,
    category_id: int | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> MinifluxFeed:
    # crawler=true tells Miniflux to fetch the original article page and extract the full
    # content (readability-style) instead of trusting the feed's own, often truncated, excerpt.
    payload: dict[str, str | int | bool] = {"feed_url": feed_url, "crawler": True}
    if category_id is not None:
        payload["category_id"] = category_id
    async with _client(transport) as client:
        response = await client.post("/v1/feeds", json=payload)
        if response.status_code >= 400:
            raise MinifluxApiError(response.text)
        return MinifluxFeed(feed_id=response.json()["feed_id"])
