from typing import Any

from worker.technical.connectors.miniflux import MinifluxConnector


def _payload(enclosures: list[dict[str, Any]] | None) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": 1,
        "title": "Episode",
        "url": "https://example.com/ep1",
        "published_at": "2026-08-12T10:00:00+00:00",
    }
    if enclosures is not None:
        entry["enclosures"] = enclosures
    return {"feed": {"id": 10, "title": "Podcast"}, "entries": [entry]}


def test_keeps_the_first_audio_enclosure() -> None:
    payload = _payload(
        [
            {"url": "https://example.com/cover.jpg", "mime_type": "image/jpeg"},
            {"url": "https://cdn.example.com/ep1.mp3", "mime_type": "audio/mpeg"},
        ]
    )

    article = MinifluxConnector().parse_webhook_payload(payload)[0]

    assert article.enclosure_url == "https://cdn.example.com/ep1.mp3"
    assert article.enclosure_type == "audio/mpeg"


def test_ignores_a_non_http_audio_enclosure() -> None:
    payload = _payload([{"url": "file:///etc/passwd", "mime_type": "audio/mpeg"}])

    article = MinifluxConnector().parse_webhook_payload(payload)[0]

    assert article.enclosure_url is None


def test_has_no_enclosure_when_the_entry_carries_none() -> None:
    article = MinifluxConnector().parse_webhook_payload(_payload(None))[0]

    assert article.enclosure_url is None
    assert article.enclosure_type is None
