import csv
import io
import json
from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import urlsplit

from api.domain.article.exceptions import InvalidReadingListError, ReadingListTooLargeError

MAX_READING_LIST_ITEMS = 2000
_ALLOWED_SCHEMES = frozenset({"http", "https"})


class ReadingListSource(StrEnum):
    POCKET = "pocket"
    WALLABAG = "wallabag"
    INSTAPAPER = "instapaper"


def parse_reading_list(source: ReadingListSource, data: bytes) -> list[str]:
    """Reads the links out of another service's export, in file order and without duplicates.

    The file is the user's but its origin is not ours to trust: every parser here is a plain
    text one (no entity expansion), links that are not http(s) are dropped, and the count is
    capped so a single upload cannot queue an unbounded amount of fetching.
    """
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidReadingListError("export is not valid UTF-8") from exc

    extract = {
        ReadingListSource.POCKET: _from_pocket,
        ReadingListSource.WALLABAG: _from_wallabag,
        ReadingListSource.INSTAPAPER: _from_instapaper,
    }[source]
    urls = _unique_web_urls(extract(text))
    if len(urls) > MAX_READING_LIST_ITEMS:
        raise ReadingListTooLargeError(f"more than {MAX_READING_LIST_ITEMS} links")
    return urls


def _unique_web_urls(candidates: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for candidate in candidates:
        url = candidate.strip()
        if urlsplit(url).scheme in _ALLOWED_SCHEMES:
            seen.setdefault(url, None)
    return list(seen)


class _AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.hrefs.append(href)


def _from_pocket(text: str) -> list[str]:
    collector = _AnchorCollector()
    collector.feed(text)
    return collector.hrefs


def _from_wallabag(text: str) -> list[str]:
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidReadingListError("export is not valid JSON") from exc
    if not isinstance(document, list):
        raise InvalidReadingListError("export is not a list of entries")
    return [
        entry["url"]
        for entry in document
        if isinstance(entry, dict) and isinstance(entry.get("url"), str)
    ]


def _from_instapaper(text: str) -> list[str]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or "URL" not in reader.fieldnames:
        raise InvalidReadingListError("export has no URL column")
    return [row["URL"] for row in reader if row.get("URL")]
