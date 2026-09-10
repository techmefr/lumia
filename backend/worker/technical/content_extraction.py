import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import httpx
import trafilatura

from api.technical.logging.external import describe_error, log_external_failure
from worker.technical.html import strip_html

_MIN_EXTRACTED_TEXT_LENGTH = 200
_USER_AGENT = "Mozilla/5.0 (compatible; LumiaBot/1.0)"
SERVICE_NAME = "page-extraction"

logger = logging.getLogger(__name__)


def _log_extraction_failure(
    *, operation: str, url: str, error: httpx.HTTPError | None = None, reason: str | None = None
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


class TrafilaturaPageExtractor:
    """Fetches an arbitrary web page and turns it into a readable article.

    Unlike ContentExtractor, there is no feed entry to fall back on here: the page is the only
    source of the title, body and metadata, so a failed fetch or an unreadable page raises.
    """

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def fetch(self, url: str) -> ExtractedPage:
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                timeout=15.0,
                follow_redirects=True,
                headers={"User-Agent": _USER_AGENT},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            _log_extraction_failure(operation="fetch_page", url=url, error=exc)
            raise PageFetchError(str(exc)) from exc

        content = trafilatura.extract(
            response.text,
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

        metadata = trafilatura.extract_metadata(response.text, default_url=url)
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

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def extract(self, url: str, fallback_html: str) -> str:
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                timeout=10.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; LumiaBot/1.0)"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            _log_extraction_failure(operation="recrawl_article", url=url, error=exc)
            return fallback_html

        extracted = trafilatura.extract(
            response.text,
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
