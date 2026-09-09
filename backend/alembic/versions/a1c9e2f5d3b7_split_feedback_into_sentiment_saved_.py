"""split feedback into sentiment/saved/favorite

Revision ID: a1c9e2f5d3b7
Revises: bb58554580c4
Create Date: 2026-08-13 12:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c9e2f5d3b7"
down_revision: str | Sequence[str] | None = "bb58554580c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user_article_feedback",
        sa.Column("saved", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "user_article_feedback",
        sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE user_article_feedback SET saved = true WHERE vote = 'SAVE'")
    op.alter_column("user_article_feedback", "vote", new_column_name="sentiment", nullable=True)
    op.execute("UPDATE user_article_feedback SET sentiment = NULL WHERE sentiment = 'SAVE'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE user_article_feedback SET sentiment = 'SAVE' WHERE saved = true")
    op.alter_column("user_article_feedback", "sentiment", new_column_name="vote", nullable=False)
    op.drop_column("user_article_feedback", "favorite")
    op.drop_column("user_article_feedback", "saved")
