import io
import zipfile
from datetime import UTC, datetime

from lxml import etree

from api.domain.article.epub_export import EpubChapter, build_epub
from api.technical.net.image_fetcher import FetchedImage

PNG = FetchedImage(media_type="image/png", data=b"\x89PNG-bytes")


class FakeImages:
    def __init__(self, available: dict[str, FetchedImage]) -> None:
        self._available = available
        self.requested: list[str] = []

    async def fetch(self, url: str) -> FetchedImage | None:
        self.requested.append(url)
        return self._available.get(url)


def _chapter(
    html: str, *, title: str = "Un titre", url: str = "https://example.com/a/b"
) -> EpubChapter:
    return EpubChapter(
        title=title,
        author="Ada",
        url=url,
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
        html=html,
    )


async def _book(chapters: list[EpubChapter], images: FakeImages) -> zipfile.ZipFile:
    data = await build_epub(title="Recueil", language="fr", chapters=chapters, images=images)
    return zipfile.ZipFile(io.BytesIO(data))


async def test_the_mimetype_comes_first_and_is_stored_uncompressed() -> None:
    book = await _book([_chapter("<p>Bonjour</p>")], FakeImages({}))

    first = book.infolist()[0]
    assert first.filename == "mimetype"
    assert first.compress_type == zipfile.ZIP_STORED
    assert book.read("mimetype") == b"application/epub+zip"


async def test_every_document_is_well_formed_xml() -> None:
    html = "<p>Fish &amp; chips<br>deux lignes</p><img src='/a.png' alt='x'>"
    book = await _book(
        [_chapter(html), _chapter("<p>Second</p>", title="Deux")],
        FakeImages({"https://example.com/a.png": PNG}),
    )

    for name in book.namelist():
        if name.endswith((".xhtml", ".opf", ".xml")):
            etree.fromstring(book.read(name))


async def test_each_article_becomes_a_chapter_listed_in_the_navigation() -> None:
    book = await _book(
        [_chapter("<p>Un</p>", title="Premier"), _chapter("<p>Deux</p>", title="Second")],
        FakeImages({}),
    )

    navigation = book.read("OEBPS/nav.xhtml").decode()
    assert "Premier" in navigation
    assert "Second" in navigation
    assert "chapter-2.xhtml" in navigation
    assert "<p>Deux</p>" in book.read("OEBPS/chapter-2.xhtml").decode()


async def test_images_are_embedded_and_the_source_points_inside_the_archive() -> None:
    images = FakeImages({"https://example.com/pics/cat.png": PNG})
    book = await _book([_chapter("<p>Un chat</p><img src='/pics/cat.png' alt='chat'>")], images)

    assert book.read("OEBPS/images/image-1.png") == PNG.data
    chapter = book.read("OEBPS/chapter-1.xhtml").decode()
    assert 'src="images/image-1.png"' in chapter
    assert "example.com/pics" not in chapter
    assert 'href="images/image-1.png"' in book.read("OEBPS/content.opf").decode()


async def test_relative_image_paths_resolve_against_the_article_url() -> None:
    images = FakeImages({"https://example.com/a/pic.png": PNG})
    await _book([_chapter("<img src='pic.png' alt=''>")], images)

    assert images.requested == ["https://example.com/a/pic.png"]


async def test_an_image_that_cannot_be_fetched_leaves_a_gap_not_a_broken_book() -> None:
    book = await _book(
        [_chapter("<p>Texte</p><img src='https://gone.example/x.png'>")], FakeImages({})
    )

    chapter = book.read("OEBPS/chapter-1.xhtml").decode()
    assert "<p>Texte</p>" in chapter
    assert "<img" not in chapter
    assert not [name for name in book.namelist() if name.startswith("OEBPS/images/")]


async def test_the_same_image_in_two_articles_is_stored_once() -> None:
    images = FakeImages({"https://example.com/logo.png": PNG})
    book = await _book(
        [
            _chapter("<img src='/logo.png' alt=''>"),
            _chapter("<img src='/logo.png' alt=''>", title="Autre"),
        ],
        images,
    )

    assert images.requested == ["https://example.com/logo.png"]
    assert [name for name in book.namelist() if name.startswith("OEBPS/images/")] == [
        "OEBPS/images/image-1.png"
    ]


async def test_scripts_frames_and_event_handlers_never_reach_the_book() -> None:
    html = (
        "<p onclick='steal()'>Lire</p><script>alert(1)</script>"
        "<iframe src='https://evil.example'></iframe><style>p{}</style>"
    )
    book = await _book([_chapter(html)], FakeImages({}))

    chapter = book.read("OEBPS/chapter-1.xhtml").decode()
    assert "<p>Lire</p>" in chapter
    for forbidden in ("script", "iframe", "onclick", "<style", "alert"):
        assert forbidden not in chapter


async def test_a_javascript_link_loses_its_target_but_keeps_its_text() -> None:
    html = "<a href='javascript:alert(1)'>piège</a> <a href='https://example.com/ok'>ok</a>"
    book = await _book([_chapter(html)], FakeImages({}))

    chapter = book.read("OEBPS/chapter-1.xhtml").decode()
    assert "javascript:" not in chapter
    assert "piège" in chapter
    assert 'href="https://example.com/ok"' in chapter


async def test_a_data_uri_image_is_dropped_without_a_download() -> None:
    images = FakeImages({})
    book = await _book([_chapter("<img src='data:image/png;base64,AAAA'>")], images)

    assert images.requested == []
    assert "<img" not in book.read("OEBPS/chapter-1.xhtml").decode()


async def test_the_metadata_carries_the_title_the_language_and_the_authors() -> None:
    book = await _book([_chapter("<p>x</p>"), _chapter("<p>y</p>", title="Autre")], FakeImages({}))

    package = book.read("OEBPS/content.opf").decode()
    assert "<dc:title>Recueil</dc:title>" in package
    assert "<dc:language>fr</dc:language>" in package
    assert package.count("<dc:creator>Ada</dc:creator>") == 1
