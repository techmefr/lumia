import pytest

from api.domain.feed.exceptions import InvalidOpmlError
from api.domain.feed.opml_parser import parse_opml

BILLION_LAUGHS = b"""<?xml version="1.0"?>
<!DOCTYPE opml [
  <!ENTITY a "dos">
  <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">
  <!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">
  <!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;">
  <!ENTITY e "&d;&d;&d;&d;&d;&d;&d;&d;&d;&d;">
  <!ENTITY f "&e;&e;&e;&e;&e;&e;&e;&e;&e;&e;">
]>
<opml version="1.0">
  <body>
    <outline type="rss" title="&f;" xmlUrl="https://example.com/feed"/>
  </body>
</opml>
"""

EXTERNAL_ENTITY = b"""<?xml version="1.0"?>
<!DOCTYPE opml [
  <!ENTITY secret SYSTEM "file:///etc/passwd">
]>
<opml version="1.0">
  <body>
    <outline type="rss" title="&secret;" xmlUrl="https://example.com/feed"/>
  </body>
</opml>
"""


@pytest.mark.parametrize("document", [BILLION_LAUGHS, EXTERNAL_ENTITY])
def test_an_entity_bearing_document_is_rejected_rather_than_expanded(document: bytes) -> None:
    with pytest.raises(InvalidOpmlError):
        parse_opml(document)


def test_a_plain_export_still_parses() -> None:
    document = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
  <body>
    <outline title="Tech">
      <outline type="rss" title="Hacker News" xmlUrl="https://hnrss.org/frontpage"/>
    </outline>
  </body>
</opml>
"""

    entries = parse_opml(document)

    assert [(entry.folder_name, entry.title, entry.url) for entry in entries] == [
        ("Tech", "Hacker News", "https://hnrss.org/frontpage")
    ]
