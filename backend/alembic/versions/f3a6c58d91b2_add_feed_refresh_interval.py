"""add feed refresh interval

Revision ID: f3a6c58d91b2
Revises: f2a91c60d4e7
Create Date: 2026-09-16 19:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a6c58d91b2"
down_revision: str | Sequence[str] | None = "f2a91c60d4e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("feeds", sa.Column("refresh_interval_minutes", sa.Integer(), nullable=True))
    op.add_column(
        "feeds", sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("feeds", "last_refreshed_at")
    op.drop_column("feeds", "refresh_interval_minutes")
