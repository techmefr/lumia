from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatAction(StrEnum):
    SUMMARIZE = "summarize"
    EXPLAIN = "explain"


class ChatMessage(Base, TimestampMixin):
    """One turn of a reader's conversation about one article, kept for that reader only."""

    __tablename__ = "chat_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), index=True)
    role: Mapped[ChatRole]
    content: Mapped[str] = mapped_column(Text)
    action: Mapped[ChatAction | None] = mapped_column(default=None)
