from typing import Any

from fastapi import APIRouter, HTTPException, status

from worker.technical.connectors.base import InvalidWebhookPayloadError
from worker.technical.connectors.miniflux import MinifluxConnector
from worker.technical.queue import get_arq_pool

router = APIRouter()

_connector = MinifluxConnector()


@router.post("/webhooks/miniflux", status_code=status.HTTP_202_ACCEPTED)
async def receive_miniflux_webhook(payload: dict[str, Any]) -> None:
    try:
        raw_articles = _connector.parse_webhook_payload(payload)
    except InvalidWebhookPayloadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from exc

    pool = await get_arq_pool()
    for article in raw_articles:
        await pool.enqueue_job("enrich_article", article)
