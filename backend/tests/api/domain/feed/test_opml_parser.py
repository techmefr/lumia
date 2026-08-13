import pytest

from api.domain.feed.exceptions import InvalidOpmlError
from api.domain.feed.opml_parser import parse_opml

FEEDLY_OPML = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
  <body>
    <outline text="Tech" title="Tech">
      <outline type="rss" text="Hacker News" title="Hacker News"
               xmlUrl="https://hnrss.org/frontpage" htmlUrl="https://news.ycombinator.com"/>
      <outline type="rss" text="Ars Technica" title="Ars Technica"
               xmlUrl="https://arstechnica.com/feed" htmlUrl="https://arstechnica.com"/>
    </outline>
    <outline type="rss" text="Uncategorized Feed" title="Uncategorized Feed"
             xmlUrl="https://example.com/feed.xml" htmlUrl="https://example.com"/>
  </body>
</opml>
"""


def test_parse_opml_extracts_feeds_grouped_by_folder() -> None:
    entries = parse_opml(FEEDLY_OPML)

    assert len(entries) == 3
    tech_entries = [entry for entry in entries if entry.folder_name == "Tech"]
    assert {entry.url for entry in tech_entries} == {
        "https://hnrss.org/frontpage",
        "https://arstechnica.com/feed",
    }


def test_parse_opml_keeps_uncategorized_feeds_without_a_folder() -> None:
    entries = parse_opml(FEEDLY_OPML)

    uncategorized = next(entry for entry in entries if entry.url == "https://example.com/feed.xml")
    assert uncategorized.folder_name is None
    assert uncategorized.title == "Uncategorized Feed"


def test_parse_opml_rejects_malformed_xml() -> None:
    with pytest.raises(InvalidOpmlError):
        parse_opml(b"not xml at all <<<")


def test_parse_opml_rejects_a_document_without_a_body() -> None:
    with pytest.raises(InvalidOpmlError):
        parse_opml(b"<opml version=\"1.0\"></opml>")
