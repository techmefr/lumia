import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI

from worker.technical.webhook import router

MINIFLUX_PAYLOAD = {
    "feed": {"id": 10, "title": "Hacker News"},
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

# Matches MINIFLUX_WEBHOOK_SECRET set in tests/conftest.py: the signature has to be computed over
# the exact bytes sent on the wire, so the body is built once and reused for both the request and
# the signature rather than re-serialised twice and risking the two falling out of sync.
_SECRET = "test-miniflux-webhook-secret"
_BODY = json.dumps(MINIFLUX_PAYLOAD).encode()


def _signature(body: bytes, secret: str = _SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app = FastAPI()
    app.include_router(router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _post(client: httpx.AsyncClient, body: bytes, signature: str | None) -> httpx.Response:
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Miniflux-Signature"] = signature
    return await client.post("/webhooks/miniflux", content=body, headers=headers)


async def test_valid_signature_enqueues_a_job_and_responds_202(client: httpx.AsyncClient) -> None:
    mock_pool = AsyncMock()
    with patch("worker.technical.webhook.get_arq_pool", AsyncMock(return_value=mock_pool)):
        response = await _post(client, _BODY, _signature(_BODY))

    assert response.status_code == 202
    mock_pool.enqueue_job.assert_awaited_once()
    assert mock_pool.enqueue_job.await_args is not None
    assert mock_pool.enqueue_job.await_args.args[0] == "enrich_article"


async def test_missing_signature_is_rejected_before_enqueueing(client: httpx.AsyncClient) -> None:
    mock_pool = AsyncMock()
    with patch("worker.technical.webhook.get_arq_pool", AsyncMock(return_value=mock_pool)):
        response = await _post(client, _BODY, None)

    assert response.status_code == 401
    mock_pool.enqueue_job.assert_not_awaited()


async def test_wrong_signature_is_rejected_before_enqueueing(client: httpx.AsyncClient) -> None:
    mock_pool = AsyncMock()
    with patch("worker.technical.webhook.get_arq_pool", AsyncMock(return_value=mock_pool)):
        response = await _post(client, _BODY, _signature(_BODY, secret="not-the-real-secret"))

    assert response.status_code == 401
    mock_pool.enqueue_job.assert_not_awaited()


async def test_signature_for_a_different_body_is_rejected(client: httpx.AsyncClient) -> None:
    # Proves the signature is checked against the body that was actually sent, not just against
    # any signature shaped like a hex digest: sign one payload, send another.
    mock_pool = AsyncMock()
    tampered = json.dumps(
        {**MINIFLUX_PAYLOAD, "feed": {"id": 999, "title": "Hacker News"}}
    ).encode()
    with patch("worker.technical.webhook.get_arq_pool", AsyncMock(return_value=mock_pool)):
        response = await _post(client, tampered, _signature(_BODY))

    assert response.status_code == 401
    mock_pool.enqueue_job.assert_not_awaited()


async def test_invalid_payload_is_rejected_before_enqueueing(client: httpx.AsyncClient) -> None:
    mock_pool = AsyncMock()
    body = json.dumps({"feed": {}, "entries": []}).encode()
    with patch("worker.technical.webhook.get_arq_pool", AsyncMock(return_value=mock_pool)):
        response = await _post(client, body, _signature(body))

    assert response.status_code == 400
    mock_pool.enqueue_job.assert_not_awaited()
