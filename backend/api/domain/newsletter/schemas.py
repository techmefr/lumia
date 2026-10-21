from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InboundMessage(BaseModel):
    """The slice of a mail a forwarder posts. Attachments and any other field are not read."""

    model_config = ConfigDict(extra="ignore")

    sender: str = Field(min_length=1, max_length=320)
    subject: str = Field(default="", max_length=998)
    html: str | None = None
    text: str | None = None
    message_id: str | None = Field(default=None, max_length=998)
    date: datetime | None = None


class NewsletterInboxStatusResponse(BaseModel):
    active: bool
    created_at: datetime | None


class NewsletterInboxCreatedResponse(BaseModel):
    token: str
    created_at: datetime
