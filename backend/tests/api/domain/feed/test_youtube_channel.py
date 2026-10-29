import httpx
import pytest

from api.domain.feed.exceptions import FeedUnreachableError
from api.domain.feed.youtube_channel import resolve_youtube_feed_url, youtube_video_id

CHANNEL_ID = "UCX6OQ3DkcsbYNE6H8uQQuVA"
FEED_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"


def _page_transport(body: str, status: int = 200) -> httpx.MockTransport:
    return httpx.MockTransport(lambda request: httpx.Response(status, text=body))


async def test_a_channel_url_resolves_to_its_feed_without_any_request() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request expected")

    resolved = await resolve_youtube_feed_url(
        f"https://www.youtube.com/channel/{CHANNEL_ID}", transport=httpx.MockTransport(refuse)
    )

    assert resolved == FEED_URL


async def test_a_handle_resolves_through_the_feed_link_of_the_channel_page() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200,
            text=f"<link rel=alternate href={chr(34)}https://www.youtube.com/feeds/videos.xml"
            f"?channel_id={CHANNEL_ID}{chr(34)}>",
        )

    resolved = await resolve_youtube_feed_url(
        "https://www.youtube.com/@MrBeast/videos", transport=httpx.MockTransport(handler)
    )

    assert resolved == FEED_URL
    assert seen == ["https://www.youtube.com/@MrBeast"]


async def test_a_handle_page_without_a_feed_link_is_unreachable() -> None:
    with pytest.raises(FeedUnreachableError):
        await resolve_youtube_feed_url(
            "https://www.youtube.com/@nobody", transport=_page_transport("<html></html>")
        )


async def test_a_failing_channel_page_is_unreachable() -> None:
    with pytest.raises(FeedUnreachableError):
        await resolve_youtube_feed_url(
            "https://www.youtube.com/@gone", transport=_page_transport("", status=404)
        )


@pytest.mark.parametrize(
    "url",
    [
        FEED_URL,
        "https://example.com/@someone",
        "https://www.youtube.com/watch?v=abc",
    ],
)
async def test_anything_else_is_left_untouched(url: str) -> None:
    assert await resolve_youtube_feed_url(url, transport=_page_transport("")) == url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=3", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/@MrBeast", None),
        ("https://example.com/watch?v=dQw4w9WgXcQ", None),
    ],
)
def test_video_id_is_read_from_a_watch_address(url: str, expected: str | None) -> None:
    assert youtube_video_id(url) == expected


async def test_a_channel_page_resolving_to_a_private_address_is_never_requested() -> None:
    with pytest.raises(FeedUnreachableError):
        await resolve_youtube_feed_url(
            "https://www.youtube.com/@MrBeast", resolve=lambda host: ["127.0.0.1"]
        )
