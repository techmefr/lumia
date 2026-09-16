"""add email digest preferences

Revision ID: c7a3f1b40d92
Revises: d5c1a70e82b4
Create Date: 2026-09-16 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7a3f1b40d92"
down_revision: str | Sequence[str] | None = "d5c1a70e82b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

digest_frequency = sa.Enum("NEVER", "DAILY", "WEEKLY", name="digestfrequency")


def upgrade() -> None:
    """Upgrade schema.

    Every existing account lands on NEVER: the digest is something a reader turns on, and a
    migration that opted the instance in would be mailing people who never asked.
    """
    digest_frequency.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column("digest_frequency", digest_frequency, nullable=False, server_default="NEVER"),
    )
    op.add_column(
        "users", sa.Column("digest_hour", sa.Integer(), nullable=False, server_default="8")
    )
    op.add_column(
        "users", sa.Column("digest_timezone", sa.String(), nullable=False, server_default="UTC")
    )
    op.add_column("users", sa.Column("digest_last_period", sa.String(), nullable=True))
    op.add_column(
        "users", sa.Column("digest_last_sent_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.alter_column("users", "digest_frequency", server_default=None)
    op.alter_column("users", "digest_hour", server_default=None)
    op.alter_column("users", "digest_timezone", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "digest_last_sent_at")
    op.drop_column("users", "digest_last_period")
    op.drop_column("users", "digest_timezone")
    op.drop_column("users", "digest_hour")
    op.drop_column("users", "digest_frequency")
    digest_frequency.drop(op.get_bind(), checkfirst=True)
