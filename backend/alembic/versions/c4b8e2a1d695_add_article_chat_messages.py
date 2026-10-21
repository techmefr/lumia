"""add article chat messages

Revision ID: c4b8e2a1d695
Revises: a3d9e1f5b742
Create Date: 2026-10-21 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4b8e2a1d695"
down_revision: str | Sequence[str] | None = "a3d9e1f5b742"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.Enum("USER", "ASSISTANT", name="chatrole"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("action", sa.Enum("SUMMARIZE", "EXPLAIN", name="chataction"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_messages_article_id"), "chat_messages", ["article_id"])
    op.create_index(op.f("ix_chat_messages_user_id"), "chat_messages", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_chat_messages_user_id"), table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_article_id"), table_name="chat_messages")
    op.drop_table("chat_messages")
    sa.Enum(name="chataction").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="chatrole").drop(op.get_bind(), checkfirst=True)
