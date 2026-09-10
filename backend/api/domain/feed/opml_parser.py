from dataclasses import dataclass
from xml.etree.ElementTree import Element

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring

from api.domain.feed.exceptions import InvalidOpmlError


@dataclass(frozen=True)
class OpmlEntry:
    folder_name: str | None
    title: str
    url: str


def parse_opml(xml_bytes: bytes) -> list[OpmlEntry]:
    """Reads a subscription export.

    The document comes from whatever produced the user's export, so it is parsed with defusedxml:
    the stdlib parser expands entities, and a few kilobytes of nested ones are enough to exhaust the
    process's memory.
    """
    try:
        root = fromstring(xml_bytes)
    except ParseError as exc:
        raise InvalidOpmlError("malformed OPML document") from exc
    except DefusedXmlException as exc:
        raise InvalidOpmlError("OPML document uses forbidden XML constructs") from exc

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


def _title(outline: Element) -> str:
    return outline.get("title") or outline.get("text") or ""
