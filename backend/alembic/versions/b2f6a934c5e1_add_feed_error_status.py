"""add feed error status

Revision ID: b2f6a934c5e1
Revises: e8b1c40d7a52
Create Date: 2026-09-11 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2f6a934c5e1"
down_revision: str | Sequence[str] | None = "e8b1c40d7a52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "feeds", sa.Column("error_count", sa.Integer(), nullable=False, server_default="0")
    )
    op.alter_column("feeds", "error_count", server_default=None)
    op.add_column("feeds", sa.Column("error_reason", sa.String(), nullable=True))
    op.add_column("feeds", sa.Column("error_since", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("feeds", "error_since")
    op.drop_column("feeds", "error_reason")
    op.drop_column("feeds", "error_count")
