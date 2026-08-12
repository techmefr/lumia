from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


class InvalidWebhookPayloadError(Exception):
    pass


@dataclass(frozen=True)
class RawArticle:
    source_type: str
    feed_external_id: str
    external_entry_id: str
    title: str
    url: str
    content: str
    published_at: datetime
    author_name: str | None = None
    category_name: str | None = None


class SourceConnector(Protocol):
    def parse_webhook_payload(self, payload: dict[str, Any]) -> list[RawArticle]: ...
