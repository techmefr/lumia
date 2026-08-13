"""add article image_url

Revision ID: bb58554580c4
Revises: 597e59b2f64c
Create Date: 2026-08-13 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bb58554580c4'
down_revision: str | Sequence[str] | None = '597e59b2f64c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('articles', sa.Column('image_url', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('articles', 'image_url')
