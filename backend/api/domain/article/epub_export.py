import asyncio
import io
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit
from uuid import UUID, uuid4
from xml.sax.saxutils import escape, quoteattr

import lxml.html
from lxml import etree

from api.technical.net.image_fetcher import FetchedImage, ImageFetcher

_MAX_IMAGES_PER_BOOK = 100
_PARALLEL_DOWNLOADS = 4
_DROPPED_TAGS = frozenset(
    {
        "script",
        "style",
        "iframe",
        "object",
        "embed",
        "form",
        "input",
        "button",
        "video",
        "audio",
        "svg",
        "noscript",
        "link",
        "meta",
    }
)
_KEPT_ATTRIBUTES = frozenset({"href", "src", "alt", "title"})
_LINK_SCHEMES = frozenset({"http", "https", "mailto"})
_IMAGE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}
_XHTML_NAMESPACES = 'xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"'


@dataclass(frozen=True)
class EpubChapter:
    title: str
    author: str | None
    url: str
    published_at: datetime
    html: str


@dataclass(frozen=True)
class _EmbeddedImage:
    name: str
    image: FetchedImage


async def build_epub(
    *,
    title: str,
    language: str,
    chapters: list[EpubChapter],
    images: ImageFetcher,
    book_id: UUID | None = None,
    now: datetime | None = None,
) -> bytes:
    """Packs articles into one EPUB 3 file that reads offline, pictures included.

    An article's images are downloaded and written into the archive: a book whose pictures still
    point at the web is empty on a reader with no connection, which is the point of a book.
    """
    trees = [_parse_body(chapter.html) for chapter in chapters]
    sources = _collect_image_sources(chapters, trees)
    embedded = await _download_images(sources, images)
    for chapter, tree in zip(chapters, trees, strict=True):
        _rewrite_images(chapter, tree, embedded)

    modified = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    identifier = f"urn:uuid:{book_id or uuid4()}"
    names = [f"chapter-{index}.xhtml" for index in range(1, len(chapters) + 1)]

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED
        )
        archive.writestr("META-INF/container.xml", _CONTAINER, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr(
            "OEBPS/content.opf",
            _package_document(title, language, chapters, identifier, modified, names, embedded),
            compress_type=zipfile.ZIP_DEFLATED,
        )
        archive.writestr(
            "OEBPS/nav.xhtml",
            _navigation_document(title, language, chapters, names),
            compress_type=zipfile.ZIP_DEFLATED,
        )
        for chapter, tree, name in zip(chapters, trees, names, strict=True):
            archive.writestr(
                f"OEBPS/{name}",
                _chapter_document(chapter, tree, language),
                compress_type=zipfile.ZIP_DEFLATED,
            )
        for entry in embedded.values():
            archive.writestr(
                f"OEBPS/images/{entry.name}", entry.image.data, compress_type=zipfile.ZIP_STORED
            )
    return buffer.getvalue()


def _parse_body(html: str) -> lxml.html.HtmlElement:
    root = lxml.html.fromstring(f"<div>{html}</div>")
    for element in list(root.iter()):
        if not isinstance(element.tag, str):
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
    for element in list(root.iter()):
        if element is root or element.getparent() is None:
            continue
        if element.tag in _DROPPED_TAGS:
            element.drop_tree()
    for element in root.iter():
        for attribute in list(element.attrib):
            if attribute not in _KEPT_ATTRIBUTES:
                del element.attrib[attribute]
        if element.tag == "a":
            _keep_link_only_if_safe(element)
    return root


def _keep_link_only_if_safe(element: lxml.html.HtmlElement) -> None:
    href = element.get("href")
    if href is not None and urlsplit(href).scheme.lower() not in _LINK_SCHEMES | {""}:
        del element.attrib["href"]


def _collect_image_sources(
    chapters: list[EpubChapter], trees: list[lxml.html.HtmlElement]
) -> list[str]:
    sources: list[str] = []
    for chapter, tree in zip(chapters, trees, strict=True):
        for image in tree.iter("img"):
            source = _absolute_source(chapter.url, image.get("src"))
            if source is not None and source not in sources:
                sources.append(source)
    return sources[:_MAX_IMAGES_PER_BOOK]


def _absolute_source(page_url: str, source: str | None) -> str | None:
    if not source:
        return None
    absolute = urljoin(page_url, source.strip())
    return absolute if urlsplit(absolute).scheme in {"http", "https"} else None


async def _download_images(sources: list[str], fetcher: ImageFetcher) -> dict[str, _EmbeddedImage]:
    gate = asyncio.Semaphore(_PARALLEL_DOWNLOADS)

    async def download(source: str) -> FetchedImage | None:
        async with gate:
            return await fetcher.fetch(source)

    fetched = await asyncio.gather(*(download(source) for source in sources))
    embedded: dict[str, _EmbeddedImage] = {}
    for source, image in zip(sources, fetched, strict=True):
        if image is None:
            continue
        extension = _IMAGE_EXTENSIONS[image.media_type]
        embedded[source] = _EmbeddedImage(
            name=f"image-{len(embedded) + 1}.{extension}", image=image
        )
    return embedded


def _rewrite_images(
    chapter: EpubChapter, tree: lxml.html.HtmlElement, embedded: dict[str, _EmbeddedImage]
) -> None:
    for image in list(tree.iter("img")):
        source = _absolute_source(chapter.url, image.get("src"))
        entry = embedded.get(source) if source is not None else None
        if entry is None:
            image.drop_tree()
            continue
        image.set("src", f"images/{entry.name}")
        image.set("alt", image.get("alt") or "")


def _chapter_document(chapter: EpubChapter, tree: lxml.html.HtmlElement, language: str) -> str:
    byline = " · ".join(
        part
        for part in (
            escape(chapter.author) if chapter.author else None,
            chapter.published_at.date().isoformat(),
        )
        if part
    )
    body = etree.tostring(tree, encoding="unicode", method="xml")
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
        f"<html {_XHTML_NAMESPACES} lang={quoteattr(language)} xml:lang={quoteattr(language)}>"
        f'<head><meta charset="utf-8"/><title>{escape(chapter.title)}</title></head>'
        f"<body><h1>{escape(chapter.title)}</h1>"
        f'<p class="meta">{byline} · <a href={quoteattr(chapter.url)}>source</a></p>'
        f"{body}</body></html>"
    )


def _navigation_document(
    title: str, language: str, chapters: list[EpubChapter], names: list[str]
) -> str:
    entries = "".join(
        f'<li><a href="{name}">{escape(chapter.title)}</a></li>'
        for chapter, name in zip(chapters, names, strict=True)
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
        f"<html {_XHTML_NAMESPACES} lang={quoteattr(language)} xml:lang={quoteattr(language)}>"
        f'<head><meta charset="utf-8"/><title>{escape(title)}</title></head>'
        f'<body><nav epub:type="toc"><h1>{escape(title)}</h1><ol>{entries}</ol></nav></body></html>'
    )


def _package_document(
    title: str,
    language: str,
    chapters: list[EpubChapter],
    identifier: str,
    modified: str,
    names: list[str],
    embedded: dict[str, _EmbeddedImage],
) -> str:
    authors = "".join(
        f"<dc:creator>{escape(author)}</dc:creator>"
        for author in dict.fromkeys(chapter.author for chapter in chapters if chapter.author)
    )
    chapter_items = "".join(
        f'<item id="chapter-{index}" href="{name}" media-type="application/xhtml+xml"/>'
        for index, name in enumerate(names, start=1)
    )
    image_items = "".join(
        f'<item id="image-{position}" href="images/{entry.name}" '
        f'media-type="{entry.image.media_type}"/>'
        for position, entry in enumerate(embedded.values(), start=1)
    )
    spine = "".join(f'<itemref idref="chapter-{index}"/>' for index in range(1, len(names) + 1))
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f'<dc:identifier id="book-id">{identifier}</dc:identifier>'
        f"<dc:title>{escape(title)}</dc:title>"
        f"<dc:language>{escape(language)}</dc:language>"
        f"{authors}"
        f'<meta property="dcterms:modified">{modified}</meta>'
        "</metadata>"
        '<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" '
        'properties="nav"/>'
        f"{chapter_items}{image_items}</manifest>"
        f"<spine>{spine}</spine></package>"
    )


_CONTAINER = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
    '<rootfiles><rootfile full-path="OEBPS/content.opf" '
    'media-type="application/oebps-package+xml"/></rootfiles></container>'
)
