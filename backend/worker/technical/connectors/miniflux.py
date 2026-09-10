from datetime import datetime
from typing import Any

from worker.technical.connectors.base import InvalidWebhookPayloadError, RawArticle


class MinifluxConnector:
    def parse_entries_payload(self, payload: dict[str, Any]) -> list[RawArticle]:
        """Reads the answer of Miniflux's entries endpoint, where each entry carries its own feed.

        Same articles as the webhook, a different envelope: the webhook groups entries under one
        feed, a query returns entries of many feeds at once.
        """
        try:
            return [
                self._to_raw_article(
                    entry,
                    feed_external_id=str(entry["feed"]["id"]),
                    category_name=_category_name(entry["feed"]),
                )
                for entry in payload["entries"]
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidWebhookPayloadError from exc

    def parse_webhook_payload(self, payload: dict[str, Any]) -> list[RawArticle]:
        try:
            feed = payload["feed"]
            # Read before the loop, so a malformed feed is refused even when the payload announces
            # no entry at all.
            feed_external_id = str(feed["id"])
            category_name = _category_name(feed)
            return [
                self._to_raw_article(
                    entry, feed_external_id=feed_external_id, category_name=category_name
                )
                for entry in payload["entries"]
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidWebhookPayloadError from exc

    def _to_raw_article(
        self, entry: dict[str, Any], *, feed_external_id: str, category_name: str | None
    ) -> RawArticle:
        return RawArticle(
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


def _category_name(feed: dict[str, Any]) -> str | None:
    category = feed.get("category")
    return str(category["title"]) if category else None
