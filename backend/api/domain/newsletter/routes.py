from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.newsletter.exceptions import EmptyMessageError, UnknownInboxError
from api.domain.newsletter.schemas import (
    InboundMessage,
    NewsletterInboxCreatedResponse,
    NewsletterInboxStatusResponse,
)
from api.domain.newsletter.service import (
    active_inbox,
    create_inbox,
    prepare_article,
    revoke_inbox,
)
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session
from api.technical.rate_limit.dependencies import client_address, enforce
from api.technical.rate_limit.limiter import RateLimiter, get_rate_limiter
from config.rate_limit import get_rate_limit_config
from worker.technical.queue import get_arq_pool

router = APIRouter()

#: A newsletter with inlined images can be big, but nothing a reader subscribes to needs more than
#: this, and the body is read in pieces so an endless one never sits whole in memory.
MAX_INBOUND_BYTES = 1024 * 1024


@router.get("/newsletters/inbox", response_model=NewsletterInboxStatusResponse)
async def read_inbox_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> NewsletterInboxStatusResponse:
    inbox = await active_inbox(session, user)
    return NewsletterInboxStatusResponse(
        active=inbox is not None, created_at=inbox.created_at if inbox else None
    )


@router.post(
    "/newsletters/inbox",
    response_model=NewsletterInboxCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_newsletter_inbox(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> NewsletterInboxCreatedResponse:
    inbox, token = await create_inbox(session, user)
    return NewsletterInboxCreatedResponse(token=token, created_at=inbox.created_at)


@router.delete("/newsletters/inbox", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_newsletter_inbox(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await revoke_inbox(session, user)


async def _read_capped(request: Request) -> bytes:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_INBOUND_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE)
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_INBOUND_BYTES:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE)
    return bytes(body)


@router.post("/inbound/newsletters/{token}", status_code=status.HTTP_202_ACCEPTED)
async def receive_newsletter(
    request: Request,
    token: str = Path(min_length=20, max_length=128),
    session: AsyncSession = Depends(get_db_session),
    limiter: RateLimiter = Depends(get_rate_limiter),
    pool: Any = Depends(get_arq_pool),
) -> None:
    """Unauthenticated on purpose, like the invitation: the token in the path is the only
    credential a mail forwarder holds."""
    config = get_rate_limit_config()
    await enforce(
        limiter,
        scope="newsletter-inbound",
        identifiers={"ip": client_address(request)},
        max_attempts=config.newsletter_inbound_max_attempts,
        window=timedelta(minutes=config.newsletter_inbound_window_minutes),
    )
    raw_body = await _read_capped(request)
    try:
        message = InboundMessage.model_validate_json(raw_body)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT) from exc
    try:
        raw_article = await prepare_article(session, token, message)
    except UnknownInboxError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except EmptyMessageError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT) from exc
    await pool.enqueue_job("enrich_article", raw_article)
