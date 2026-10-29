"""add the per-user session version that revokes access tokens

Revision ID: d4e7a2c91b58
Revises: d4e7f0a23b54
Create Date: 2026-10-29 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4e7a2c91b58"
down_revision: str | Sequence[str] | None = "d4e7f0a23b54"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("session_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "session_version")
