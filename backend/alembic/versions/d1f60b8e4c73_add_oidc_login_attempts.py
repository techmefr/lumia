"""add oidc login attempts

Revision ID: d1f60b8e4c73
Revises: b4e17d80c9a2
Create Date: 2026-09-10 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1f60b8e4c73"
down_revision: str | Sequence[str] | None = "a7e35c1d90f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "oidc_login_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("nonce", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("oidc_login_attempts")
