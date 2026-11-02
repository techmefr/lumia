"""recompute the stored bytes counter for databases migrated before the table was locked

Revision ID: e9b3c5a17d42
Revises: d4e7a2c91b58
Create Date: 2026-11-02 10:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
from api.domain.instance.usage_triggers import BACKFILL, LOCK_ARTICLES, LOCK_TIMEOUT

revision: str = "e9b3c5a17d42"
down_revision: str | Sequence[str] | None = "d4e7a2c91b58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(LOCK_TIMEOUT)
    op.execute(LOCK_ARTICLES)
    op.execute(BACKFILL)


def downgrade() -> None:
    """Downgrade schema."""
