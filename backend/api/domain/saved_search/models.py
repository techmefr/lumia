from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class SavedSearch(Base, TimestampMixin):
    """A named query over the reader's own articles, optionally scoped to one feed or folder.

    `alert` promotes it: the worker then checks every newly stored article against it. The scope
    is stored as ids rather than copied names so a renamed feed keeps matching.
    """

    __tablename__ = "saved_searches"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_saved_searches_user_name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str]
    query: Mapped[str]
    feed_id: Mapped[UUID | None] = mapped_column(ForeignKey("feeds.id"), default=None)
    folder_id: Mapped[UUID | None] = mapped_column(ForeignKey("folders.id"), default=None)
    alert: Mapped[bool] = mapped_column(default=False)


class AlertNotification(Base, TimestampMixin):
    """One alert hit. The unique pair is what keeps a re-processed article from notifying twice."""

    __tablename__ = "alert_notifications"
    __table_args__ = (
        UniqueConstraint(
            "saved_search_id", "article_id", name="uq_alert_notifications_search_article"
        ),
        Index("ix_alert_notifications_user_read", "user_id", "read"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    saved_search_id: Mapped[UUID] = mapped_column(ForeignKey("saved_searches.id"))
    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"))
    read: Mapped[bool] = mapped_column(default=False)
