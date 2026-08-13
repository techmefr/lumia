"""add read flag and manual source type

Revision ID: c7f1a4e82b93
Revises: a1c9e2f5d3b7
Create Date: 2026-08-13 15:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c7f1a4e82b93'
down_revision: str | Sequence[str] | None = 'a1c9e2f5d3b7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'user_article_feedback',
        sa.Column('read', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Postgres forbids ALTER TYPE ... ADD VALUE inside a transaction block before 12; on 12+ it is
    # allowed but the new value can't be used in the same transaction, which is fine here since no
    # row is written to it by this migration.
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'MANUAL'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres cannot drop a single enum value; the MANUAL feeds would have to be deleted and the
    # type recreated. Leaving the value in place is harmless and keeps the downgrade reversible.
    op.drop_column('user_article_feedback', 'read')
