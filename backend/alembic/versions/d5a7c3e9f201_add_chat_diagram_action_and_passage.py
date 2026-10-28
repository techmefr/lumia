"""add chat diagram action and passage

Revision ID: d5a7c3e9f201
Revises: c4e8a2f61b93
Create Date: 2026-10-28 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5a7c3e9f201"
down_revision: str | Sequence[str] | None = "c4e8a2f61b93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("chat_messages", sa.Column("passage", sa.Text(), nullable=True))
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE chataction ADD VALUE IF NOT EXISTS 'DIAGRAM'")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("chat_messages", "passage")
