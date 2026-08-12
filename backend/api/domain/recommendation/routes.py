from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.recommendation.feedback_service import apply_feedback
from api.domain.recommendation.schemas import FeedbackRequest
from api.domain.user.models import User
from api.technical.auth.middleware import get_current_user
from api.technical.db import get_db_session

router = APIRouter()


@router.post("/articles/{article_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def send_feedback(
    article_id: UUID,
    payload: FeedbackRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    article = await session.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await apply_feedback(session, user_id=user.id, article_id=article_id, vote=payload.vote)
