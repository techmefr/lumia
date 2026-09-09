import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Request, status

from config.miniflux import get_miniflux_config
from worker.technical.connectors.base import InvalidWebhookPayloadError
from worker.technical.connectors.miniflux import MinifluxConnector
from worker.technical.queue import get_arq_pool

router = APIRouter()

_connector = MinifluxConnector()

_SIGNATURE_HEADER = "X-Miniflux-Signature"


def _has_valid_signature(raw_body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    secret = get_miniflux_config().miniflux_webhook_secret.encode()
    expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    # Constant-time on purpose: a naive == leaks how many leading characters matched, which turns
    # the check into an oracle an attacker can brute-force one byte at a time.
    return hmac.compare_digest(expected, signature)


@router.post("/webhooks/miniflux", status_code=status.HTTP_202_ACCEPTED)
async def receive_miniflux_webhook(request: Request) -> None:
    raw_body = await request.body()
    if not _has_valid_signature(raw_body, request.headers.get(_SIGNATURE_HEADER)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        raw_articles = _connector.parse_webhook_payload(await request.json())
    except InvalidWebhookPayloadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from exc

    pool = await get_arq_pool()
    for article in raw_articles:
        await pool.enqueue_job("enrich_article", article)
