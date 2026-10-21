from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.chat import chat_service
from api.domain.chat.exceptions import ArticleNotFoundError, ChatUnavailableError
from api.domain.chat.schemas import ChatMessageResponse, ChatSendRequest
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.domain.user.providers import get_chat_client
from api.technical.db import get_db_session
from api.technical.rate_limit.dependencies import client_address, enforce
from api.technical.rate_limit.limiter import RateLimiter, get_rate_limiter
from config.chat import get_chat_config
from worker.technical.ai.base import ChatClient

router = APIRouter()


@router.get("/articles/{article_id}/chat", response_model=list[ChatMessageResponse])
async def list_chat(
    article_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ChatMessageResponse]:
    try:
        messages = await chat_service.list_messages(session, user.id, article_id)
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return [ChatMessageResponse.model_validate(message) for message in messages]


@router.post("/articles/{article_id}/chat", response_model=list[ChatMessageResponse])
async def send_chat_message(
    article_id: UUID,
    payload: ChatSendRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    client: ChatClient | None = Depends(get_chat_client),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> list[ChatMessageResponse]:
    """The reader's question and the model's answer, as the two turns that were just stored.

    Unavailable rather than failed when the account has no usable provider: the client can then
    point the reader to the settings instead of showing an error.
    """
    try:
        article = await chat_service.find_article(session, user.id, article_id)
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="no_ai_provider"
        )
    config = get_chat_config()
    await enforce(
        limiter,
        scope="chat",
        identifiers={"ip": client_address(request), "user": str(user.id)},
        max_attempts=config.chat_rate_limit_max_attempts,
        window=timedelta(minutes=config.chat_rate_limit_window_minutes),
    )
    try:
        messages = await chat_service.send(
            session,
            client,
            user_id=user.id,
            article=article,
            message=payload.message,
            action=payload.action,
        )
    except ChatUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="chat_failed") from exc
    return [ChatMessageResponse.model_validate(message) for message in messages]


@router.delete("/articles/{article_id}/chat", status_code=status.HTTP_204_NO_CONTENT)
async def clear_chat(
    article_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    try:
        await chat_service.clear(session, user.id, article_id)
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
