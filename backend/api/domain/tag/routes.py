import logging
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.routes import load_own_article
from api.domain.tag import service
from api.domain.tag.ai_suggestions import suggest_with_ai
from api.domain.tag.exceptions import TagNameTakenError, TagNotFoundError
from api.domain.tag.models import Tag
from api.domain.tag.schemas import (
    TagNameRequest,
    TagRef,
    TagResponse,
    TagSuggestionResponse,
)
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.domain.user.providers import get_chat_client
from api.technical.db import get_db_session
from worker.technical.ai.base import ChatClient, LlmApiError
from worker.technical.html import strip_html

logger = logging.getLogger(__name__)

router = APIRouter()


def _refs(tags: list[Tag]) -> list[TagRef]:
    return [TagRef(id=tag.id, name=tag.name) for tag in tags]


async def _own_tag(session: AsyncSession, user: User, tag_id: UUID) -> Tag:
    try:
        return await service.get_tag(session, user.id, tag_id)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc


@router.get("/tags", response_model=list[TagResponse])
async def list_tags(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[TagResponse]:
    return [
        TagResponse(id=tag.id, name=tag.name, article_count=count)
        for tag, count in await service.list_tags(session, user.id)
    ]


@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: TagNameRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TagResponse:
    try:
        tag = await service.create_tag(session, user.id, payload.name)
    except TagNameTakenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="tag_name_taken") from exc
    return TagResponse(id=tag.id, name=tag.name, article_count=0)


@router.patch("/tags/{tag_id}", response_model=TagResponse)
async def rename_tag(
    tag_id: UUID,
    payload: TagNameRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TagResponse:
    try:
        tag = await service.rename_tag(session, user.id, tag_id, payload.name)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except TagNameTakenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="tag_name_taken") from exc
    return TagResponse(
        id=tag.id, name=tag.name, article_count=await service.count_articles(session, tag.id)
    )


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await service.delete_tag(session, user.id, tag_id)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc


@router.post("/articles/{article_id}/tags", response_model=list[TagRef])
async def tag_article(
    article_id: UUID,
    payload: TagNameRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[TagRef]:
    article = await load_own_article(session, article_id, user)
    return _refs(await service.attach_by_name(session, user.id, article.id, payload.name))


@router.delete("/articles/{article_id}/tags/{tag_id}", response_model=list[TagRef])
async def untag_article(
    article_id: UUID,
    tag_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[TagRef]:
    article = await load_own_article(session, article_id, user)
    try:
        return _refs(await service.detach(session, user.id, article.id, tag_id))
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc


@router.get("/articles/{article_id}/tag-suggestions", response_model=list[TagSuggestionResponse])
async def get_tag_suggestions(
    article_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[TagSuggestionResponse]:
    article = await load_own_article(session, article_id, user)
    return await service.suggest_tags(session, user.id, article.id)


@router.post(
    "/articles/{article_id}/tag-suggestions/ai", response_model=list[TagSuggestionResponse]
)
async def get_ai_tag_suggestions(
    article_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    chat_client: ChatClient | None = Depends(get_chat_client),
) -> list[TagSuggestionResponse]:
    """Asks the account's own model, only when the reader asks: it costs them tokens."""
    article = await load_own_article(session, article_id, user)
    if chat_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="no_ai_provider"
        )
    carried = await service.carried_slugs(session, user.id, article.id)
    try:
        return await suggest_with_ai(
            chat_client,
            title=article.title,
            text=strip_html(article.content),
            excluded=carried,
        )
    except (LlmApiError, httpx.HTTPError) as exc:
        logger.warning("ai tag suggestion failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="ai_suggestion_failed"
        ) from exc
