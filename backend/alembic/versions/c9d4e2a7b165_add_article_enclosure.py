"""add the audio enclosure of an article

Revision ID: c9d4e2a7b165
Revises: a3d9e1f5b742
Create Date: 2026-10-21 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c9d4e2a7b165"
down_revision: str | Sequence[str] | None = "a3d9e1f5b742"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("enclosure_url", sa.String(), nullable=True))
    op.add_column("articles", sa.Column("enclosure_type", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("articles", "enclosure_type")
    op.drop_column("articles", "enclosure_url")
