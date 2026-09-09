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


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app = FastAPI()
    app.include_router(router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def test_valid_payload_enqueues_a_job_and_responds_202(client: httpx.AsyncClient) -> None:
    mock_pool = AsyncMock()
    with patch("worker.technical.webhook.get_arq_pool", AsyncMock(return_value=mock_pool)):
        response = await client.post("/webhooks/miniflux", json=MINIFLUX_PAYLOAD)

    assert response.status_code == 202
    mock_pool.enqueue_job.assert_awaited_once()
    assert mock_pool.enqueue_job.await_args is not None
    assert mock_pool.enqueue_job.await_args.args[0] == "enrich_article"


async def test_invalid_payload_is_rejected_before_enqueueing(client: httpx.AsyncClient) -> None:
    mock_pool = AsyncMock()
    with patch("worker.technical.webhook.get_arq_pool", AsyncMock(return_value=mock_pool)):
        response = await client.post("/webhooks/miniflux", json={"feed": {}, "entries": []})

    assert response.status_code == 400
    mock_pool.enqueue_job.assert_not_awaited()
