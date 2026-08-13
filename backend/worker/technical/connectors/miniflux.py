from datetime import datetime
from typing import Any

from worker.technical.connectors.base import InvalidWebhookPayloadError, RawArticle


class MinifluxConnector:
    def parse_webhook_payload(self, payload: dict[str, Any]) -> list[RawArticle]:
        try:
            feed = payload["feed"]
            feed_external_id = str(feed["id"])
            category = feed.get("category")
            category_name = category["title"] if category else None
            return [
                RawArticle(
                    source_type="miniflux",
                    feed_external_id=feed_external_id,
                    external_entry_id=str(entry["id"]),
                    title=entry["title"],
                    url=entry["url"],
                    content=entry.get("content", ""),
                    published_at=datetime.fromisoformat(entry["published_at"]),
                    author_name=entry.get("author") or None,
                    category_name=category_name,
                )
                for entry in payload["entries"]
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidWebhookPayloadError from exc
