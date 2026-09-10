"""add refresh token rotation columns

Revision ID: c9d4f2a71b58
Revises: b4e17d80c9a2
Create Date: 2026-09-10 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d4f2a71b58"
down_revision: str | Sequence[str] | None = "b4e17d80c9a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "refresh_tokens",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "refresh_tokens",
        sa.Column(
            "family_id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
    )
    # The default exists only to fill the rows already in the table; every new row carries the
    # family it was issued into, chosen in Python like the rest of this schema's defaults.
    op.alter_column("refresh_tokens", "family_id", server_default=None)
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "family_id")
    op.drop_column("refresh_tokens", "revoked_at")
