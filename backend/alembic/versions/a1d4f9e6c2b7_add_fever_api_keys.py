"""add fever api keys

Revision ID: a1d4f9e6c2b7
Revises: c7a3f1b40d92
Create Date: 2026-09-19 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1d4f9e6c2b7"
down_revision: str | Sequence[str] | None = "c7a3f1b40d92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "fever_api_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("digest", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_fever_api_keys_user_id"),
        sa.UniqueConstraint("digest", name="uq_fever_api_keys_digest"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("fever_api_keys")
