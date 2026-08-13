from typing import Protocol

import httpx
import trafilatura

from worker.technical.html import strip_html

_MIN_EXTRACTED_TEXT_LENGTH = 200


class ContentExtractor(Protocol):
    async def extract(self, url: str, fallback_html: str) -> str: ...


def get_content_extractor_transport() -> httpx.AsyncBaseTransport | None:
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
        except httpx.HTTPError:
            return fallback_html

        extracted = trafilatura.extract(
            response.text,
            output_format="html",
            include_images=True,
            include_links=False,
            favor_recall=True,
        )
        if not extracted or len(strip_html(extracted)) < _MIN_EXTRACTED_TEXT_LENGTH:
            return fallback_html
        return str(extracted)
