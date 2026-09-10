import httpx
import pytest

from worker.technical.content_extraction import (
    PageFetchError,
    TrafilaturaContentExtractor,
    TrafilaturaPageExtractor,
)

_PAGE_HTML = "<html><body><article><p>Du contenu.</p></article></body></html>"


def _resolving_to_the_public_internet(host: str) -> list[str]:
    return ["93.184.216.34"]


def _resolving_to_loopback(host: str) -> list[str]:
    return ["127.0.0.1"]


def _serving(html: str = _PAGE_HTML) -> tuple[httpx.MockTransport, list[str]]:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, text=html)

    return httpx.MockTransport(handler), requested


async def test_a_url_off_the_public_internet_is_never_requested() -> None:
    transport, requested = _serving()
    extractor = TrafilaturaPageExtractor(transport=transport, resolve=_resolving_to_loopback)

    with pytest.raises(PageFetchError):
        await extractor.fetch("http://169.254.169.254/latest/meta-data/")

    assert requested == []


async def test_a_non_http_scheme_is_refused() -> None:
    transport, requested = _serving()
    extractor = TrafilaturaPageExtractor(
        transport=transport, resolve=_resolving_to_the_public_internet
    )

    with pytest.raises(PageFetchError):
        await extractor.fetch("file:///etc/passwd")

    assert requested == []


async def test_every_redirect_hop_is_checked_not_just_the_first() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://internal.test/secret"})

    def resolve(host: str) -> list[str]:
        return ["93.184.216.34"] if host == "example.com" else ["127.0.0.1"]

    extractor = TrafilaturaPageExtractor(transport=httpx.MockTransport(handler), resolve=resolve)

    with pytest.raises(PageFetchError):
        await extractor.fetch("https://example.com/a")

    assert requested == ["https://example.com/a"]


async def test_a_redirect_loop_gives_up() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://example.com/next"})

    extractor = TrafilaturaPageExtractor(
        transport=httpx.MockTransport(handler), resolve=_resolving_to_the_public_internet
    )

    with pytest.raises(PageFetchError):
        await extractor.fetch("https://example.com/a")


async def test_a_body_over_the_cap_is_refused() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * (5 * 1024 * 1024 + 1))

    extractor = TrafilaturaPageExtractor(
        transport=httpx.MockTransport(handler), resolve=_resolving_to_the_public_internet
    )

    with pytest.raises(PageFetchError):
        await extractor.fetch("https://example.com/huge")


async def test_the_re_crawl_falls_back_to_the_feed_content_when_the_url_is_blocked() -> None:
    transport, requested = _serving()
    extractor = TrafilaturaContentExtractor(transport=transport, resolve=_resolving_to_loopback)

    result = await extractor.extract("http://router.local/a", "<p>fallback</p>")

    assert result == "<p>fallback</p>"
    assert requested == []
