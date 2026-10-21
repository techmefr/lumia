import re
from urllib.parse import parse_qs, urlsplit

import httpx

from api.domain.feed.exceptions import FeedUnreachableError

_YOUTUBE_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com"})
_CHANNEL_PATH = re.compile(r"^/channel/(UC[\w-]{22})/?")
_CHANNEL_PAGE_PATH = re.compile(r"^/(@[\w.\-]+|c/[^/]+|user/[^/]+)")
_FEED_LINK = re.compile(r"feeds/videos\.xml\?channel_id=(UC[\w-]{22})")
_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
_PAGE_TIMEOUT_SECONDS = 10.0
_MAX_PAGE_CHARS = 2 * 1024 * 1024


def _is_youtube(url: str) -> bool:
    return urlsplit(url).hostname in _YOUTUBE_HOSTS


def youtube_video_id(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.hostname == "youtu.be":
        return parts.path.lstrip("/") or None
    if parts.hostname in _YOUTUBE_HOSTS and parts.path == "/watch":
        values = parse_qs(parts.query).get("v")
        return values[0] if values else None
    return None


async def resolve_youtube_feed_url(
    url: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> str:
    """Turns a channel address a reader would paste into the channel's own Atom feed.

    Anything that is not a YouTube channel address comes back untouched. A /channel/UC... address
    carries the identifier; a handle or legacy name does not, so the channel page is fetched once
    and the identifier is read from its feed autodiscovery link, the same one a feed reader uses.
    """
    if not _is_youtube(url):
        return url
    path = urlsplit(url).path
    direct = _CHANNEL_PATH.match(path)
    if direct is not None:
        return _FEED_URL.format(channel_id=direct.group(1))
    page = _CHANNEL_PAGE_PATH.match(path)
    if page is None:
        return url
    channel_id = await _channel_id_from_page(f"https://www.youtube.com{page.group(0)}", transport)
    return _FEED_URL.format(channel_id=channel_id)


async def _channel_id_from_page(page_url: str, transport: httpx.AsyncBaseTransport | None) -> str:
    try:
        async with httpx.AsyncClient(
            transport=transport, timeout=_PAGE_TIMEOUT_SECONDS, follow_redirects=False
        ) as client:
            response = await client.get(page_url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise FeedUnreachableError from exc
    match = _FEED_LINK.search(response.text[:_MAX_PAGE_CHARS])
    if match is None:
        raise FeedUnreachableError
    return match.group(1)
