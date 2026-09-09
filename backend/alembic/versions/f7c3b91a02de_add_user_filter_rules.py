"""add user filter rules and the anthropic ai provider

Revision ID: f7c3b91a02de
Revises: e5a2d7c40b18
Create Date: 2026-08-14 10:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7c3b91a02de"
down_revision: str | Sequence[str] | None = "e5a2d7c40b18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

filter_mode = sa.Enum("BOOST", "MUTE", name="filtermode")
# The column reuses the type created above rather than declaring it again: passed to create_table as
# it is, sqlalchemy emits a second CREATE TYPE and the whole chain fails on a fresh database.
filter_mode_column = postgresql.ENUM("BOOST", "MUTE", name="filtermode", create_type=False)


def upgrade() -> None:
    """Upgrade schema."""
    filter_mode.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "user_filter_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("term", sa.String(), nullable=False),
        sa.Column("mode", filter_mode_column, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "term", "mode", name="uq_user_filter_rules_user_term_mode"),
    )
    op.create_index("ix_user_filter_rules_user_id", "user_filter_rules", ["user_id"], unique=False)
    # Anthropic's messages api is not openai-compatible, so it is a provider of its own rather
    # than a base-url variant of the shared client.
    op.execute("ALTER TYPE aiprovider ADD VALUE IF NOT EXISTS 'ANTHROPIC'")


def downgrade() -> None:
    """Downgrade schema.

    The ANTHROPIC enum value is left in place: postgres cannot drop a value from an enum, and
    rebuilding the type would mean rewriting the users table for a reversal nobody runs.
    """
    op.drop_index("ix_user_filter_rules_user_id", table_name="user_filter_rules")
    op.drop_table("user_filter_rules")
    filter_mode.drop(op.get_bind(), checkfirst=True)
