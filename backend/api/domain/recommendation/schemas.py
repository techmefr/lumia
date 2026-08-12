from pydantic import BaseModel

from api.domain.recommendation.models import Vote


class FeedbackRequest(BaseModel):
    vote: Vote
