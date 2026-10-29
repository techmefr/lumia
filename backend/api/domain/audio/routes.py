import logging
from datetime import timedelta
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.audio.service import find_cached_audio, store_audio, voice_hash
from api.domain.feed.models import Feed
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.domain.user.providers import get_speech_synthesizer
from api.technical.db import get_db_session
from api.technical.net.url_guard import (
    BlockedUrlError,
    Resolver,
    ensure_public_http_url,
    get_url_resolver,
)
from api.technical.rate_limit.dependencies import client_address, enforce
from api.technical.rate_limit.limiter import RateLimiter, get_rate_limiter
from config.tts import get_tts_config
from worker.technical.html import strip_html
from worker.technical.speech.base import SpeechApiError, SpeechSynthesizer

logger = logging.getLogger(__name__)

router = APIRouter()

BYTES_PER_MB = 1024 * 1024


@router.get("/articles/{article_id}/audio")
async def get_article_audio(
    article_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    synthesizer: SpeechSynthesizer | None = Depends(get_speech_synthesizer),
    limiter: RateLimiter = Depends(get_rate_limiter),
    resolver: Resolver = Depends(get_url_resolver),
) -> Response:
    """The article read aloud by the account's own speech provider, generated once and then kept.

    Unavailable rather than failed when nothing is configured or the article is too long to be
    worth synthesising: the reader's browser voice takes over, which is why every refusal here has
    a stable `detail` the client can act on.
    """
    article = await session.scalar(
        select(Article)
        .join(Feed, Feed.id == Article.feed_id)
        .where(Article.id == article_id, Feed.user_id == user.id)
    )
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if synthesizer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="no_tts_provider"
        )

    config = get_tts_config()
    voice = voice_hash(synthesizer.cache_key)
    cached = await find_cached_audio(session, user_id=user.id, article_id=article.id, voice=voice)
    if cached is not None:
        return _audio_response(cached.data, cached.content_type)

    text = f"{article.title}. {strip_html(article.content)}"
    if len(text) > config.tts_max_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="article_too_long"
        )
    if not config.tts_allow_private_endpoints:
        try:
            ensure_public_http_url(synthesizer.base_url, resolve=resolver)
        except BlockedUrlError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="tts_endpoint_blocked"
            ) from exc
    await enforce(
        limiter,
        scope="tts",
        identifiers={"ip": client_address(request), "user": str(user.id)},
        max_attempts=config.tts_rate_limit_max_attempts,
        window=timedelta(minutes=config.tts_rate_limit_window_minutes),
    )
    try:
        audio = await synthesizer.synthesize(text)
    except BlockedUrlError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="tts_endpoint_blocked"
        ) from exc
    except (SpeechApiError, httpx.HTTPError) as exc:
        logger.warning("speech synthesis failed: %s", type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="tts_failed") from exc
    if len(audio.data) > config.tts_max_audio_mb * BYTES_PER_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="audio_too_large"
        )
    await store_audio(
        session,
        user_id=user.id,
        article_id=article.id,
        voice=voice,
        audio=audio,
        cache_limit_mb=config.tts_cache_mb_per_account,
    )
    return _audio_response(audio.data, audio.content_type)


def _audio_response(data: bytes, content_type: str) -> Response:
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )
