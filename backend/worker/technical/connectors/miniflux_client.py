import base64
import binascii
import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

from api.technical.logging.external import log_external_failure
from config.miniflux import get_miniflux_config
from worker.technical.connectors.base import RawArticle
from worker.technical.connectors.miniflux import MinifluxConnector

SERVICE_NAME = "miniflux"

logger = logging.getLogger(__name__)


class MinifluxApiError(Exception):
    pass


def _api_error(operation: str, response: httpx.Response) -> MinifluxApiError:
    log_external_failure(
        logger,
        service=SERVICE_NAME,
        operation=operation,
        url=str(response.request.url),
        status_code=response.status_code,
    )
    return MinifluxApiError(response.text)


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
class MinifluxFeedDetail:
    feed_id: int
    title: str
    parsing_error_count: int
    parsing_error_message: str


@dataclass(frozen=True)
class MinifluxKnownFeed:
    feed_id: int
    title: str
    feed_url: str
    parsing_error_count: int
    parsing_error_message: str


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
            raise _api_error("list_categories", response)
        return [
            MinifluxNamedCategory(category_id=item["id"], title=item["title"])
            for item in response.json()
        ]


async def list_feeds(
    *, transport: httpx.AsyncBaseTransport | None = None
) -> list[MinifluxKnownFeed]:
    """Every feed the instance carries, including the ones no Lumia reader subscribes to."""
    async with _client(transport) as client:
        response = await client.get("/v1/feeds")
        if response.status_code >= 400:
            raise _api_error("list_feeds", response)
        return [
            MinifluxKnownFeed(
                feed_id=item["id"],
                title=item.get("title") or item["feed_url"],
                feed_url=item["feed_url"],
                parsing_error_count=item.get("parsing_error_count") or 0,
                parsing_error_message=item.get("parsing_error_message") or "",
            )
            for item in response.json()
        ]


async def list_recent_entries(
    *,
    published_after: datetime,
    limit: int,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[RawArticle]:
    """Lists the entries Miniflux published since a point in time, newest first."""
    async with _client(transport) as client:
        response = await client.get(
            "/v1/entries",
            params={
                "published_after": int(published_after.timestamp()),
                "limit": limit,
                "order": "published_at",
                "direction": "desc",
            },
        )
        if response.status_code >= 400:
            raise MinifluxApiError(response.text)
        return MinifluxConnector().parse_entries_payload(response.json())


async def create_category(
    title: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> MinifluxCategory:
    async with _client(transport) as client:
        response = await client.post("/v1/categories", json={"title": title})
        if response.status_code >= 400:
            raise _api_error("create_category", response)
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
            raise _api_error("create_feed", response)
        return MinifluxFeed(feed_id=response.json()["feed_id"])


@dataclass(frozen=True)
class MinifluxFeedIcon:
    mime_type: str
    data: bytes


async def get_feed_icon(
    feed_id: int, *, transport: httpx.AsyncBaseTransport | None = None
) -> MinifluxFeedIcon | None:
    """Returns the feed's own icon, or None when Miniflux has none for it.

    Miniflux answers with `data` as "<mime>;base64,<payload>" rather than a raw body, so the
    payload has to be split off and decoded before it can be served as an image.
    """
    async with _client(transport) as client:
        response = await client.get(f"/v1/feeds/{feed_id}/icon")
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise _api_error("get_feed_icon", response)

        payload = response.json()
        raw = str(payload.get("data", ""))
        _, _, encoded = raw.partition("base64,")
        if not encoded:
            return None
        try:
            data = base64.b64decode(encoded)
        except (ValueError, binascii.Error):
            return None
        return MinifluxFeedIcon(mime_type=str(payload.get("mime_type", "image/png")), data=data)


async def get_feed(
    feed_id: int, *, transport: httpx.AsyncBaseTransport | None = None
) -> MinifluxFeedDetail:
    async with _client(transport) as client:
        response = await client.get(f"/v1/feeds/{feed_id}")
        if response.status_code >= 400:
            raise _api_error("get_feed", response)
        data = response.json()
        return MinifluxFeedDetail(
            feed_id=data["id"],
            title=data["title"],
            parsing_error_count=data.get("parsing_error_count") or 0,
            parsing_error_message=data.get("parsing_error_message") or "",
        )


async def refresh_feed(feed_id: int, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
    """Asks Miniflux to fetch the feed right now, instead of waiting for its own poll cycle."""
    async with _client(transport) as client:
        response = await client.post(f"/v1/feeds/{feed_id}/refresh")
        if response.status_code >= 400:
            raise _api_error("refresh_feed", response)
