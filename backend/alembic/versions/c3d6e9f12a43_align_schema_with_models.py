"""align the schema with the models so alembic check passes

Revision ID: c3d6e9f12a43
Revises: b2c5d8e01f32
Create Date: 2026-10-29 09:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d6e9f12a43"
down_revision: str | Sequence[str] | None = "b2c5d8e01f32"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE playlists DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE tags DROP COLUMN IF EXISTS updated_at")


def downgrade() -> None:
    """Downgrade schema."""
    for table in ("playlists", "tags"):
        op.add_column(
            table,
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.alter_column(table, "updated_at", server_default=None)
