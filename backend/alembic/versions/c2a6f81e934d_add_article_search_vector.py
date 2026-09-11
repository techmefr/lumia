"""add article search vector

Revision ID: c2a6f81e934d
Revises: e8b1c40d7a52
Create Date: 2026-09-11 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2a6f81e934d"
down_revision: str | Sequence[str] | None = "e8b1c40d7a52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# original_lang only ever holds "FR" or "EN" (the postgres "lang" enum's member names — see Lang in
# api/domain/article/models.py), so a two-way CASE is enough to pick the regconfig; both branches are
# immutable, which a generated column requires. The column is computed by postgres itself rather than
# kept in sync from python: nothing short of a database trigger stays correct across every write path
# that touches an article.
_SEARCH_VECTOR_EXPRESSION = """
CASE original_lang
    WHEN 'EN' THEN to_tsvector('english', title || ' ' || coalesce(summary, '') || ' ' || content)
    ELSE to_tsvector('french', title || ' ' || coalesce(summary, '') || ' ' || content)
END
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "articles",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(_SEARCH_VECTOR_EXPRESSION, persisted=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_articles_search_vector",
        "articles",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_articles_search_vector", table_name="articles")
    op.drop_column("articles", "search_vector")
