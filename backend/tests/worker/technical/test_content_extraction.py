import httpx

from worker.technical.content_extraction import TrafilaturaContentExtractor


def _resolving_to_the_public_internet(host: str) -> list[str]:
    return ["93.184.216.34"]


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

    extractor = TrafilaturaContentExtractor(
        transport=httpx.MockTransport(handler), resolve=_resolving_to_the_public_internet
    )
    result = await extractor.extract("https://example.com/a", "<p>fallback</p>")

    assert "premier paragraphe du contenu reel" in result
    assert "Mentions legales" not in result


async def test_extract_falls_back_to_the_feed_content_when_the_fetch_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    extractor = TrafilaturaContentExtractor(
        transport=httpx.MockTransport(handler), resolve=_resolving_to_the_public_internet
    )
    result = await extractor.extract("https://example.com/a", "<p>fallback</p>")

    assert result == "<p>fallback</p>"


async def test_extract_falls_back_when_the_page_yields_no_extractable_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body><nav>menu only</nav></body></html>")

    extractor = TrafilaturaContentExtractor(
        transport=httpx.MockTransport(handler), resolve=_resolving_to_the_public_internet
    )
    result = await extractor.extract("https://example.com/a", "<p>fallback</p>")

    assert result == "<p>fallback</p>"
