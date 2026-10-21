"""add feedback read_at

Revision ID: a4d82e6b1c75
Revises: a4d82f9e1b36
Create Date: 2026-10-21 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4d82e6b1c75"
down_revision: str | Sequence[str] | None = "a4d82f9e1b36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Rows already read are dated by the moment their feedback row was created: the real instant was
    never recorded, and that is the closest thing that was.
    """
    op.add_column(
        "user_article_feedback", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute("UPDATE user_article_feedback SET read_at = created_at WHERE read")
    op.create_index("ix_user_article_feedback_read_at", "user_article_feedback", ["read_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_user_article_feedback_read_at", table_name="user_article_feedback")
    op.drop_column("user_article_feedback", "read_at")
