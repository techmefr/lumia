"""add manual tags

Revision ID: a3d9e1f5b742
Revises: a3e9b7d21c64
Create Date: 2026-10-21 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3d9e1f5b742"
down_revision: str | Sequence[str] | None = ("a3d9e1c5b742", "b8e3a51c7d04")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "slug", name="uq_tags_user_slug"),
    )
    op.create_index("ix_tags_user_id", "tags", ["user_id"], unique=False)
    op.create_table(
        "article_tags",
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("article_id", "tag_id"),
    )
    op.create_index("ix_article_tags_tag_id", "article_tags", ["tag_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_article_tags_tag_id", table_name="article_tags")
    op.drop_table("article_tags")
    op.drop_index("ix_tags_user_id", table_name="tags")
    op.drop_table("tags")
