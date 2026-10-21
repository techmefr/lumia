"""add article highlights

Revision ID: a3e9b7d21c64
Revises: a4d82e6b1c75, a91d3e57b2c4
Create Date: 2026-10-21 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3e9b7d21c64"
down_revision: str | Sequence[str] | None = ("a4d82e6b1c75", "a91d3e57b2c4")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "highlights",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("prefix", sa.Text(), nullable=False),
        sa.Column("suffix", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_highlights_article_id"), "highlights", ["article_id"])
    op.create_index(op.f("ix_highlights_user_id"), "highlights", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_highlights_user_id"), table_name="highlights")
    op.drop_index(op.f("ix_highlights_article_id"), table_name="highlights")
    op.drop_table("highlights")
