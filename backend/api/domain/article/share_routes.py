from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.routes import load_own_article
from api.domain.article.schemas import (
    ArticleShareCreatedResponse,
    ArticleShareStatusResponse,
    PublicArticleResponse,
)
from api.domain.article.share_service import (
    PublicSharingDisabledError,
    active_share,
    create_share,
    find_shared_article,
    revoke_shares,
    sanitize_shared_html,
)
from api.domain.instance.settings_service import get_instance
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session
from api.technical.rate_limit.dependencies import client_address, enforce
from api.technical.rate_limit.limiter import RateLimiter, get_rate_limiter
from config.rate_limit import get_rate_limit_config

router = APIRouter()

#: A public page has no business being indexed, cached by a shared proxy or leaking its own
#: address through a Referer header. `no-store` also keeps a revoked link from lingering in a cache.
PUBLIC_RESPONSE_HEADERS = {
    "X-Robots-Tag": "noindex, nofollow, noarchive",
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
}


@router.get("/articles/{article_id}/share", response_model=ArticleShareStatusResponse)
async def read_share_status(
    article_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ArticleShareStatusResponse:
    await load_own_article(session, article_id, user)
    instance = await get_instance(session)
    share = await active_share(session, user, article_id)
    return ArticleShareStatusResponse(
        enabled=instance.public_sharing_enabled,
        shared=share is not None and instance.public_sharing_enabled,
        created_at=share.created_at if share else None,
    )


@router.post(
    "/articles/{article_id}/share",
    response_model=ArticleShareCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_article_share(
    article_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ArticleShareCreatedResponse:
    article = await load_own_article(session, article_id, user)
    instance = await get_instance(session)
    try:
        share, token = await create_share(
            session, user, article, sharing_enabled=instance.public_sharing_enabled
        )
    except PublicSharingDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="public_sharing_disabled"
        ) from exc
    return ArticleShareCreatedResponse(token=token, created_at=share.created_at)


@router.delete("/articles/{article_id}/share", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_article_share(
    article_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await load_own_article(session, article_id, user)
    await revoke_shares(session, user, article_id)


@router.get("/public/articles/{token}", response_model=PublicArticleResponse)
async def read_public_article(
    request: Request,
    response: Response,
    token: str = Path(min_length=20, max_length=128),
    session: AsyncSession = Depends(get_db_session),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> PublicArticleResponse:
    config = get_rate_limit_config()
    await enforce(
        limiter,
        scope="public-share",
        identifiers={"ip": client_address(request)},
        max_attempts=config.public_share_max_attempts,
        window=timedelta(minutes=config.public_share_window_minutes),
    )
    instance = await get_instance(session)
    article = await find_shared_article(session, token) if instance.public_sharing_enabled else None
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, headers=PUBLIC_RESPONSE_HEADERS)
    response.headers.update(PUBLIC_RESPONSE_HEADERS)
    return PublicArticleResponse(
        title=article.title,
        content=sanitize_shared_html(article.content),
        url=article.url,
        published_at=article.published_at,
        author_name=article.author.name if article.author else None,
        image_url=article.image_url,
        language=article.original_lang.value,
    )
