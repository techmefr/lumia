from dataclasses import dataclass
from xml.etree import ElementTree

from api.domain.feed.exceptions import InvalidOpmlError


@dataclass(frozen=True)
class OpmlEntry:
    folder_name: str | None
    title: str
    url: str


def parse_opml(xml_bytes: bytes) -> list[OpmlEntry]:
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as exc:
        raise InvalidOpmlError("malformed OPML document") from exc

    body = root.find("body")
    if body is None:
        raise InvalidOpmlError("OPML document has no <body>")

    entries: list[OpmlEntry] = []
    for outline in body.findall("outline"):
        xml_url = outline.get("xmlUrl")
        if xml_url is not None:
            entries.append(OpmlEntry(folder_name=None, title=_title(outline), url=xml_url))
            continue
        folder_name = _title(outline)
        for child in outline.findall("outline"):
            child_url = child.get("xmlUrl")
            if child_url is None:
                continue
            entries.append(OpmlEntry(folder_name=folder_name, title=_title(child), url=child_url))
    return entries


def _title(outline: ElementTree.Element) -> str:
    return outline.get("title") or outline.get("text") or ""
