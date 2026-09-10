import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import httpx
import trafilatura

from api.technical.logging.external import describe_error, log_external_failure
from api.technical.net.url_guard import (
    BlockedUrlError,
    Resolver,
    ensure_public_http_url,
    resolve_with_system,
)
from worker.technical.html import strip_html

_MIN_EXTRACTED_TEXT_LENGTH = 200
_USER_AGENT = "Mozilla/5.0 (compatible; LumiaBot/1.0)"
_MAX_BODY_BYTES = 5 * 1024 * 1024
_MAX_REDIRECTS = 5

SERVICE_NAME = "page-extraction"

logger = logging.getLogger(__name__)


def _log_extraction_failure(
    *, operation: str, url: str, error: BaseException | None = None, reason: str | None = None
) -> None:
    status_code = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
    log_external_failure(
        logger,
        service=SERVICE_NAME,
        operation=operation,
        url=url,
        status_code=status_code,
        error=describe_error(error) if error is not None else reason,
    )


class ContentExtractor(Protocol):
    async def extract(self, url: str, fallback_html: str) -> str: ...


@dataclass(frozen=True)
class ExtractedPage:
    title: str
    content: str
    image_url: str | None = None
    author: str | None = None
    published_at: datetime | None = None


class PageFetchError(Exception):
    pass


class PageExtractor(Protocol):
    async def fetch(self, url: str) -> ExtractedPage: ...


def get_content_extractor_transport() -> httpx.AsyncBaseTransport | None:
    return None


async def fetch_page_html(
    url: str,
    *,
    transport: httpx.AsyncBaseTransport | None,
    timeout: float,
    resolve: Resolver,
) -> str:
    """Fetches a page the instance was asked to read, refusing anything that isn't the public web.

    Redirects are followed by hand: httpx would chase them for us, but then only the first hop
    would ever be checked and a public URL redirecting to `127.0.0.1` would walk straight past the
    guard. The body is capped for the same reason a timeout exists — an endless response is a way
    to take the instance down without ever answering.
    """
    current_url = url
    for _ in range(_MAX_REDIRECTS + 1):
        ensure_public_http_url(current_url, resolve=resolve)
        async with (
            httpx.AsyncClient(
                transport=transport,
                timeout=timeout,
                follow_redirects=False,
                headers={"User-Agent": _USER_AGENT},
            ) as client,
            client.stream("GET", current_url) as response,
        ):
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise PageFetchError("redirect without a location")
                current_url = str(response.url.join(location))
                continue
            response.raise_for_status()
            return await _read_capped_text(response)
    raise PageFetchError(f"more than {_MAX_REDIRECTS} redirects")


async def _read_capped_text(response: httpx.Response) -> str:
    body = bytearray()
    async for chunk in response.aiter_bytes():
        body += chunk
        if len(body) > _MAX_BODY_BYTES:
            raise PageFetchError(f"page body over {_MAX_BODY_BYTES} bytes")
    return body.decode(response.charset_encoding or "utf-8", errors="replace")


class TrafilaturaPageExtractor:
    """Fetches an arbitrary web page and turns it into a readable article.

    Unlike ContentExtractor, there is no feed entry to fall back on here: the page is the only
    source of the title, body and metadata, so a failed fetch or an unreadable page raises.
    """

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        resolve: Resolver = resolve_with_system,
    ) -> None:
        self._transport = transport
        self._resolve = resolve

    async def fetch(self, url: str) -> ExtractedPage:
        try:
            html = await fetch_page_html(
                url, transport=self._transport, timeout=15.0, resolve=self._resolve
            )
        except httpx.HTTPError as exc:
            _log_extraction_failure(operation="fetch_page", url=url, error=exc)
            raise PageFetchError(str(exc)) from exc
        except BlockedUrlError as exc:
            raise PageFetchError(str(exc)) from exc

        content = trafilatura.extract(
            html,
            output_format="html",
            include_images=True,
            include_links=False,
            favor_recall=True,
        )
        if not content or len(strip_html(content)) < _MIN_EXTRACTED_TEXT_LENGTH:
            _log_extraction_failure(
                operation="fetch_page", url=url, reason="no readable content extracted"
            )
            raise PageFetchError("no readable content extracted")

        metadata = trafilatura.extract_metadata(html, default_url=url)
        return ExtractedPage(
            title=(getattr(metadata, "title", None) or url),
            content=str(content),
            image_url=getattr(metadata, "image", None),
            author=getattr(metadata, "author", None),
            published_at=_parse_date(getattr(metadata, "date", None)),
        )


def get_page_extractor() -> PageExtractor:
    return TrafilaturaPageExtractor()


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class TrafilaturaContentExtractor:
    """Re-crawls the article's own page and re-extracts its main content.

    Feed-crawler extraction (e.g. Miniflux's) sometimes leaks surrounding site
    chrome (nav, category lists) into the entry content. Trafilatura's own
    boilerplate removal on a fresh page fetch tends to be cleaner, so it's
    preferred whenever the fetch and extraction both succeed; any failure or
    a suspiciously short result falls back to the feed-provided content.
    """

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        resolve: Resolver = resolve_with_system,
    ) -> None:
        self._transport = transport
        self._resolve = resolve

    async def extract(self, url: str, fallback_html: str) -> str:
        try:
            html = await fetch_page_html(
                url, transport=self._transport, timeout=10.0, resolve=self._resolve
            )
        except (httpx.HTTPError, PageFetchError, BlockedUrlError) as exc:
            _log_extraction_failure(operation="recrawl_article", url=url, error=exc)
            return fallback_html

        extracted = trafilatura.extract(
            html,
            output_format="html",
            include_images=True,
            include_links=False,
            favor_recall=True,
        )
        if not extracted or len(strip_html(extracted)) < _MIN_EXTRACTED_TEXT_LENGTH:
            _log_extraction_failure(
                operation="recrawl_article", url=url, reason="no readable content extracted"
            )
            return fallback_html
        return str(extracted)
