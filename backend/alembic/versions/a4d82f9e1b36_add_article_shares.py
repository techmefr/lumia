"""add article shares and the instance public sharing switch

Revision ID: a4d82f9e1b36
Revises: c7a3f1b40d92
Create Date: 2026-10-21 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4d82f9e1b36"
down_revision: str | Sequence[str] | None = "c7a3f1b40d92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # The default only fills the rows that already exist; it is dropped right after so the column
    # keeps taking its value from the Python side, like every other one in this schema.
    op.add_column(
        "instances",
        sa.Column(
            "public_sharing_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.alter_column("instances", "public_sharing_enabled", server_default=None)

    op.create_table(
        "article_shares",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_article_shares_article_id"), "article_shares", ["article_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_article_shares_article_id"), table_name="article_shares")
    op.drop_table("article_shares")
    op.drop_column("instances", "public_sharing_enabled")
