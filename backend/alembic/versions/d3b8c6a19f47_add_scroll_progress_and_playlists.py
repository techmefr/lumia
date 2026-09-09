"""add scroll progress and playlists

Revision ID: d3b8c6a19f47
Revises: c7f1a4e82b93
Create Date: 2026-08-13 16:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3b8c6a19f47"
down_revision: str | Sequence[str] | None = "c7f1a4e82b93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user_article_feedback",
        sa.Column("scroll_progress", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_table(
        "playlists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "playlist_items",
        sa.Column("playlist_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"]),
        sa.PrimaryKeyConstraint("playlist_id", "article_id"),
        sa.UniqueConstraint("playlist_id", "article_id", name="uq_playlist_items_playlist_article"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("playlist_items")
    op.drop_table("playlists")
    op.drop_column("user_article_feedback", "scroll_progress")
