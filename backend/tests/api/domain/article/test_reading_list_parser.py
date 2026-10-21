import json

import pytest

from api.domain.article.exceptions import InvalidReadingListError, ReadingListTooLargeError
from api.domain.article.reading_list_parser import (
    MAX_READING_LIST_ITEMS,
    ReadingListSource,
    parse_reading_list,
)

POCKET = b"""<!DOCTYPE html><html><body><h1>Unread</h1><ul>
<li><a href="https://example.com/a" time_added="1" tags="x">A</a></li>
<li><a href="https://example.com/b">B</a></li>
<li><a href="https://example.com/a">A again</a></li>
<li><a href="javascript:alert(1)">bad</a></li>
<li><a href="file:///etc/passwd">bad</a></li>
</ul></body></html>"""


def test_a_pocket_export_yields_its_web_links_once_in_order() -> None:
    assert parse_reading_list(ReadingListSource.POCKET, POCKET) == [
        "https://example.com/a",
        "https://example.com/b",
    ]


def test_a_wallabag_export_yields_the_url_of_each_entry() -> None:
    export = json.dumps(
        [{"url": "https://example.com/a", "title": "A"}, {"title": "no url"}, "junk"]
    ).encode()

    assert parse_reading_list(ReadingListSource.WALLABAG, export) == ["https://example.com/a"]


def test_a_wallabag_export_that_is_not_a_list_is_refused() -> None:
    with pytest.raises(InvalidReadingListError):
        parse_reading_list(ReadingListSource.WALLABAG, b'{"url": "https://example.com"}')


def test_a_wallabag_export_that_is_not_json_is_refused() -> None:
    with pytest.raises(InvalidReadingListError):
        parse_reading_list(ReadingListSource.WALLABAG, b"<html>")


def test_an_instapaper_export_yields_the_url_column() -> None:
    export = (
        b"URL,Title,Selection,Folder,Timestamp\n"
        b"https://example.com/a,A,,Unread,1\n"
        b",empty,,Unread,2\n"
        b'"https://example.com/b?x=1,2",B,,Archive,3\n'
    )

    assert parse_reading_list(ReadingListSource.INSTAPAPER, export) == [
        "https://example.com/a",
        "https://example.com/b?x=1,2",
    ]


def test_an_instapaper_export_without_a_url_column_is_refused() -> None:
    with pytest.raises(InvalidReadingListError):
        parse_reading_list(ReadingListSource.INSTAPAPER, b"Title\nA\n")


def test_a_file_that_is_not_utf8_is_refused() -> None:
    with pytest.raises(InvalidReadingListError):
        parse_reading_list(ReadingListSource.POCKET, b"\xff\xfe\x00")


def test_an_export_over_the_item_cap_is_refused() -> None:
    links = "".join(
        f'<a href="https://example.com/{n}">x</a>' for n in range(MAX_READING_LIST_ITEMS + 1)
    )

    with pytest.raises(ReadingListTooLargeError):
        parse_reading_list(ReadingListSource.POCKET, links.encode())


def test_entities_in_a_pocket_file_are_not_expanded_into_a_bomb() -> None:
    bomb = b'<!DOCTYPE x [<!ENTITY a "dos">]><a href="https://example.com/&a;">x</a>'

    assert parse_reading_list(ReadingListSource.POCKET, bomb) == ["https://example.com/&a;"]
