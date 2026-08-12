from datetime import UTC, datetime

import pytest

from worker.technical.connectors.base import InvalidWebhookPayloadError
from worker.technical.connectors.miniflux import MinifluxConnector

MINIFLUX_PAYLOAD = {
    "feed": {"id": 10, "title": "Hacker News", "category": {"title": "Tech"}},
    "entries": [
        {
            "id": 123,
            "title": "Some title",
            "url": "https://example.com/a",
            "content": "<p>body</p>",
            "author": "Jane Doe",
            "published_at": "2026-08-12T10:00:00+00:00",
        }
    ],
}


def test_parse_webhook_payload_normalizes_an_entry_into_a_raw_article() -> None:
    articles = MinifluxConnector().parse_webhook_payload(MINIFLUX_PAYLOAD)
    assert len(articles) == 1
    article = articles[0]
    assert article.feed_external_id == "10"
    assert article.external_entry_id == "123"
    assert article.title == "Some title"
    assert article.url == "https://example.com/a"
    assert article.content == "<p>body</p>"
    assert article.author_name == "Jane Doe"
    assert article.category_name == "Tech"
    assert article.published_at == datetime(2026, 8, 12, 10, 0, tzinfo=UTC)


def test_parse_webhook_payload_handles_a_feed_without_category() -> None:
    payload = {
        "feed": {"id": 11, "title": "No category feed"},
        "entries": [
            {
                "id": 456,
                "title": "Another title",
                "url": "https://example.com/b",
                "content": "",
                "author": "",
                "published_at": "2026-08-12T10:00:00+00:00",
            }
        ],
    }
    article = MinifluxConnector().parse_webhook_payload(payload)[0]
    assert article.category_name is None
    assert article.author_name is None


def test_parse_webhook_payload_rejects_a_payload_missing_a_required_field() -> None:
    payload = {"feed": {"id": 10}, "entries": [{"id": 123, "title": "Missing url"}]}
    with pytest.raises(InvalidWebhookPayloadError):
        MinifluxConnector().parse_webhook_payload(payload)
