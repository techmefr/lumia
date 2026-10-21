"""add fever ids and keys

Revision ID: b8d3f1a7c250
Revises: a3e9b7d21c64
Create Date: 2026-10-21 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8d3f1a7c250"
down_revision: str | Sequence[str] | None = "a3e9b7d21c64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FEVER_ID_TABLES = ("articles", "feeds", "folders")


def upgrade() -> None:
    """Upgrade schema."""
    for table in FEVER_ID_TABLES:
        op.add_column(
            table,
            sa.Column("fever_id", sa.BigInteger(), sa.Identity(), nullable=False, unique=True),
        )
    op.create_table(
        "fever_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("fever_keys")
    for table in FEVER_ID_TABLES:
        op.drop_column(table, "fever_id")
