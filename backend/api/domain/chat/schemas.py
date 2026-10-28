from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from api.domain.chat.models import ChatAction, ChatRole
from config.chat import get_chat_config


class ChatSendRequest(BaseModel):
    message: str | None = None
    action: ChatAction | None = None
    passage: str | None = None

    @model_validator(mode="after")
    def _exactly_one_of_message_and_action(self) -> Self:
        if self.message is not None:
            self.message = self.message.strip()
        has_message = bool(self.message)
        if has_message == (self.action is not None):
            raise ValueError("send either a message or an action")
        if len(self.message or "") > get_chat_config().chat_max_message_chars:
            raise ValueError("message too long")
        if self.passage is not None:
            self.passage = self.passage.strip() or None
        if len(self.passage or "") > get_chat_config().chat_max_passage_chars:
            raise ValueError("passage too long")
        if self.action == ChatAction.DIAGRAM and self.passage is not None:
            raise ValueError("a diagram covers the whole article")
        return self


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: ChatRole
    content: str
    action: ChatAction | None
    passage: str | None
    created_at: datetime
