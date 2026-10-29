"""keep each account's stored bytes as a counter maintained by the database

Revision ID: d4e7f0a23b54
Revises: c3d6e9f12a43
Create Date: 2026-10-29 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from api.domain.instance.usage_triggers import (
    BACKFILL,
    CREATE_FUNCTION,
    CREATE_TRIGGER,
    DROP_FUNCTION,
    DROP_TRIGGER,
)

revision: str = "d4e7f0a23b54"
down_revision: str | Sequence[str] | None = "c3d6e9f12a43"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("stored_bytes", sa.BigInteger(), server_default="0", nullable=False),
    )
    op.execute(BACKFILL)
    op.execute(CREATE_FUNCTION)
    op.execute(CREATE_TRIGGER)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(DROP_TRIGGER)
    op.execute(DROP_FUNCTION)
    op.drop_column("users", "stored_bytes")
