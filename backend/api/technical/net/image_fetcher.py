import asyncio
from dataclasses import dataclass
from typing import Protocol

import httpx

from api.technical.net.url_guard import (
    BlockedUrlError,
    Resolver,
    ensure_public_http_url,
    resolve_with_system,
)

_USER_AGENT = "Mozilla/5.0 (compatible; LumiaBot/1.0)"
_MAX_IMAGE_BYTES = 5 * 1024 * 1024
_MAX_REDIRECTS = 3
_TIMEOUT_SECONDS = 10.0
# SVG is left out: it is the one image type that can carry a script, and an e-reader renders it.
ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/gif", "image/webp"})


@dataclass(frozen=True)
class FetchedImage:
    media_type: str
    data: bytes


class ImageFetcher(Protocol):
    async def fetch(self, url: str) -> FetchedImage | None: ...


class GuardedImageFetcher:
    """Downloads an image found in an article, or says there is none worth embedding.

    A missing image is not an error for the caller: an export that fails because one picture is
    gone from its host is worse than a book with a gap. Anything that is not a plain public image
    under the size cap therefore comes back as `None`.
    """

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        resolve: Resolver = resolve_with_system,
    ) -> None:
        self._transport = transport
        self._resolve = resolve

    async def fetch(self, url: str) -> FetchedImage | None:
        try:
            return await self._fetch(url)
        except (BlockedUrlError, httpx.HTTPError, ValueError):
            return None

    async def _fetch(self, url: str) -> FetchedImage | None:
        current_url = url
        for _ in range(_MAX_REDIRECTS + 1):
            await asyncio.to_thread(ensure_public_http_url, current_url, resolve=self._resolve)
            async with (
                httpx.AsyncClient(
                    transport=self._transport,
                    timeout=_TIMEOUT_SECONDS,
                    follow_redirects=False,
                    headers={"User-Agent": _USER_AGENT},
                ) as client,
                client.stream("GET", current_url) as response,
            ):
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        return None
                    current_url = str(response.url.join(location))
                    continue
                response.raise_for_status()
                media_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if media_type not in ALLOWED_IMAGE_TYPES:
                    return None
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body += chunk
                    if len(body) > _MAX_IMAGE_BYTES:
                        return None
                return FetchedImage(media_type=media_type, data=bytes(body))
        return None


def get_image_fetcher() -> ImageFetcher:
    return GuardedImageFetcher()
