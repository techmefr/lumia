"""add related_articles

Revision ID: a1c4e29f6b83
Revises: c7a3f1b40d92
Create Date: 2026-09-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c4e29f6b83"
down_revision: str | Sequence[str] | None = "c7a3f1b40d92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "related_articles",
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("related_article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["related_article_id"], ["articles.id"]),
        sa.PrimaryKeyConstraint("article_id", "related_article_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("related_articles")
