from pydantic import BaseModel

from api.domain.recommendation.models import Vote


class FeedbackRequest(BaseModel):
    sentiment: Vote | None = None
    saved: bool | None = None
    favorite: bool | None = None
