"""add saved searches and alert notifications

Revision ID: a3d9e1c5b742
Revises: a9d41e7b3c60, b8c3e1f47a26
Create Date: 2026-10-21 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3d9e1c5b742"
down_revision: str | Sequence[str] | None = ("a9d41e7b3c60", "b8c3e1f47a26")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "saved_searches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("query", sa.String(), nullable=False),
        sa.Column("feed_id", sa.Uuid(), nullable=True),
        sa.Column("folder_id", sa.Uuid(), nullable=True),
        sa.Column("alert", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["feed_id"], ["feeds.id"]),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_saved_searches_user_name"),
    )
    op.create_index("ix_saved_searches_user_id", "saved_searches", ["user_id"], unique=False)
    op.create_table(
        "alert_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("saved_search_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["saved_search_id"], ["saved_searches.id"]),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "saved_search_id", "article_id", name="uq_alert_notifications_search_article"
        ),
    )
    op.create_index(
        "ix_alert_notifications_user_read", "alert_notifications", ["user_id", "read"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_alert_notifications_user_read", table_name="alert_notifications")
    op.drop_table("alert_notifications")
    op.drop_index("ix_saved_searches_user_id", table_name="saved_searches")
    op.drop_table("saved_searches")
