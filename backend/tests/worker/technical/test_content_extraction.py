import logging

import httpx
import pytest

from worker.technical.content_extraction import (
    PageFetchError,
    TrafilaturaContentExtractor,
    TrafilaturaPageExtractor,
)

_PAGE_HTML = """
<html>
<body>
<nav><a href="/cat/1">Actualites</a><a href="/cat/2">Securite</a></nav>
<article>
<h1>Un vrai titre d'article</h1>
<p>Voici le premier paragraphe du contenu reel de l'article, suffisamment long
pour que trafilatura le retienne comme corps principal de la page plutot que
comme du bruit de navigation.</p>
<p>Un second paragraphe qui developpe encore le sujet avec plusieurs phrases
completes pour renforcer la detection du contenu principal par l'extracteur.</p>
</article>
<footer><a href="/legal">Mentions legales</a></footer>
</body>
</html>
"""


async def test_extract_returns_the_cleaned_main_content_when_the_fetch_succeeds() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_PAGE_HTML)

    extractor = TrafilaturaContentExtractor(transport=httpx.MockTransport(handler))
    result = await extractor.extract("https://example.com/a", "<p>fallback</p>")

    assert "premier paragraphe du contenu reel" in result
    assert "Mentions legales" not in result


async def test_extract_falls_back_to_the_feed_content_when_the_fetch_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    extractor = TrafilaturaContentExtractor(transport=httpx.MockTransport(handler))
    result = await extractor.extract("https://example.com/a", "<p>fallback</p>")

    assert result == "<p>fallback</p>"


async def test_extract_falls_back_when_the_page_yields_no_extractable_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body><nav>menu only</nav></body></html>")

    extractor = TrafilaturaContentExtractor(transport=httpx.MockTransport(handler))
    result = await extractor.extract("https://example.com/a", "<p>fallback</p>")

    assert result == "<p>fallback</p>"


async def test_recrawl_falls_back_and_logs_the_status_of_an_unreachable_page(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    extractor = TrafilaturaContentExtractor(transport=httpx.MockTransport(handler))
    with caplog.at_level(logging.WARNING):
        content = await extractor.extract("https://example.test/a?token=secret", "<p>feed</p>")

    assert content == "<p>feed</p>"
    record = caplog.records[-1]
    assert record.service == "page-extraction"  # type: ignore[attr-defined]
    assert record.operation == "recrawl_article"  # type: ignore[attr-defined]
    assert record.status_code == 503  # type: ignore[attr-defined]
    assert record.url == "https://example.test/a"  # type: ignore[attr-defined]


async def test_page_fetch_logs_the_reason_when_the_page_has_no_readable_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body><p>trop court</p></body></html>")

    extractor = TrafilaturaPageExtractor(transport=httpx.MockTransport(handler))
    with caplog.at_level(logging.WARNING), pytest.raises(PageFetchError):
        await extractor.fetch("https://example.test/a")

    record = caplog.records[-1]
    assert record.operation == "fetch_page"  # type: ignore[attr-defined]
    assert record.error == "no readable content extracted"  # type: ignore[attr-defined]


async def test_page_fetch_logs_the_status_of_an_unreachable_page(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="gone")

    extractor = TrafilaturaPageExtractor(transport=httpx.MockTransport(handler))
    with caplog.at_level(logging.WARNING), pytest.raises(PageFetchError):
        await extractor.fetch("https://example.test/missing")

    record = caplog.records[-1]
    assert record.service == "page-extraction"  # type: ignore[attr-defined]
    assert record.status_code == 404  # type: ignore[attr-defined]
    assert record.url == "https://example.test/missing"  # type: ignore[attr-defined]
