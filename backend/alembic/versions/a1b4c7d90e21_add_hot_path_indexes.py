"""add the indexes the hot queries were missing

Revision ID: a1b4c7d90e21
Revises: f4d9a1b73c82
Create Date: 2026-10-29 09:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "a1b4c7d90e21"
down_revision: str | Sequence[str] | None = "f4d9a1b73c82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEXES: tuple[tuple[str, str], ...] = (
    ("articles", "feed_id"),
    ("articles", "published_at"),
    ("articles", "author_id"),
    ("articles", "category_id"),
    ("feeds", "user_id"),
    ("feeds", "external_feed_id"),
    ("feeds", "folder_id"),
    ("folders", "user_id"),
    ("article_keywords", "keyword_id"),
    ("user_article_feedback", "article_id"),
    ("refresh_tokens", "user_id"),
    ("refresh_tokens", "expires_at"),
    ("magic_link_tokens", "user_id"),
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for table, column in INDEXES:
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_{table}_{column} ON {table} ({column})"
            )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for table, column in INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS ix_{table}_{column}")
