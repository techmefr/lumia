from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.domain.webhook.exceptions import WebhookLimitReachedError, WebhookNotFoundError
from api.domain.webhook.models import OutboundWebhook, WebhookEvent
from api.domain.webhook.schemas import (
    DeliveryResponse,
    WebhookCreatedResponse,
    WebhookCreateRequest,
    WebhookResponse,
    WebhookUpdateRequest,
)
from api.domain.webhook.service import (
    create_webhook,
    delete_webhook,
    list_deliveries,
    list_webhooks,
    update_webhook,
)
from api.technical.db import get_db_session
from api.technical.net.url_guard import BlockedUrlError, Resolver, get_url_resolver

router = APIRouter()


def _to_response(webhook: OutboundWebhook) -> WebhookResponse:
    return WebhookResponse(
        id=webhook.id,
        url=webhook.url,
        events=[WebhookEvent(event) for event in webhook.events],
        active=webhook.active,
        created_at=webhook.created_at,
    )


@router.get("/outbound-webhooks", response_model=list[WebhookResponse])
async def get_outbound_webhooks(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[WebhookResponse]:
    return [_to_response(webhook) for webhook in await list_webhooks(session, user.id)]


@router.post(
    "/outbound-webhooks",
    response_model=WebhookCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_outbound_webhook(
    payload: WebhookCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    resolve: Resolver = Depends(get_url_resolver),
) -> WebhookCreatedResponse:
    try:
        webhook, secret = await create_webhook(
            session, user.id, url=payload.url, events=payload.events, resolve=resolve
        )
    except BlockedUrlError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="webhook_url_blocked"
        ) from exc
    except WebhookLimitReachedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="webhook_limit_reached"
        ) from exc
    return WebhookCreatedResponse(**_to_response(webhook).model_dump(), secret=secret)


@router.patch("/outbound-webhooks/{webhook_id}", response_model=WebhookResponse)
async def patch_outbound_webhook(
    webhook_id: UUID,
    payload: WebhookUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    resolve: Resolver = Depends(get_url_resolver),
) -> WebhookResponse:
    try:
        webhook = await update_webhook(
            session,
            user.id,
            webhook_id,
            url=payload.url,
            events=payload.events,
            active=payload.active,
            resolve=resolve,
        )
    except WebhookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except BlockedUrlError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="webhook_url_blocked"
        ) from exc
    return _to_response(webhook)


@router.delete("/outbound-webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_outbound_webhook(
    webhook_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await delete_webhook(session, user.id, webhook_id)
    except WebhookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc


@router.get("/outbound-webhooks/{webhook_id}/deliveries", response_model=list[DeliveryResponse])
async def get_webhook_deliveries(
    webhook_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[DeliveryResponse]:
    try:
        deliveries = await list_deliveries(session, user.id, webhook_id)
    except WebhookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return [
        DeliveryResponse(
            id=delivery.id,
            event=WebhookEvent(delivery.event),
            status=delivery.status,
            attempts=delivery.attempts,
            last_status_code=delivery.last_status_code,
            last_error=delivery.last_error,
            created_at=delivery.created_at,
            delivered_at=delivery.delivered_at,
        )
        for delivery in deliveries
    ]
