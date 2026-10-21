from datetime import datetime

from pydantic import BaseModel


class FeverKeyStatusResponse(BaseModel):
    enabled: bool
    created_at: datetime | None


class FeverKeyCreatedResponse(BaseModel):
    email: str
    secret: str
    created_at: datetime
