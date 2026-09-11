from xml.etree.ElementTree import Element, SubElement, tostring

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.feed.models import Feed, Folder, SourceType
from api.domain.user.models import User


async def export_opml(session: AsyncSession, user: User) -> bytes:
    """Builds the OPML document a reader would need to leave with their subscriptions.

    Rebuilt from Lumia's own folders and feeds rather than proxying Miniflux's own export: the
    reader's folders and retouched titles live here, not on the instance. The synthetic feed that
    holds pages saved by URL carries no real address, so it is not a subscription and is left out.
    """
    folders = list(await session.scalars(select(Folder).where(Folder.user_id == user.id)))
    feeds = list(
        await session.scalars(
            select(Feed).where(Feed.user_id == user.id, Feed.source_type != SourceType.MANUAL)
        )
    )

    root = Element("opml", version="1.0")
    head = SubElement(root, "head")
    SubElement(head, "title").text = "Lumia subscriptions"
    body = SubElement(root, "body")

    feeds_by_folder_id: dict[str, list[Feed]] = {}
    unfiled: list[Feed] = []
    for feed in feeds:
        if feed.folder_id is None:
            unfiled.append(feed)
        else:
            feeds_by_folder_id.setdefault(str(feed.folder_id), []).append(feed)

    for folder in folders:
        folder_feeds = feeds_by_folder_id.get(str(folder.id), [])
        outline = SubElement(body, "outline", text=folder.name, title=folder.name)
        for feed in folder_feeds:
            _append_feed_outline(outline, feed)

    for feed in unfiled:
        _append_feed_outline(body, feed)

    xml_bytes: bytes = tostring(root, encoding="UTF-8", xml_declaration=True)
    return xml_bytes


def _append_feed_outline(parent: Element, feed: Feed) -> None:
    SubElement(
        parent,
        "outline",
        type="rss",
        text=feed.title,
        title=feed.title,
        xmlUrl=feed.url,
    )
