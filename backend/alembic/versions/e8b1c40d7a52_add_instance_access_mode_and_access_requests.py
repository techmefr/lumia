"""add instance access mode and access requests

Revision ID: e8b1c40d7a52
Revises: b4e17d80c9a2
Create Date: 2026-09-10 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8b1c40d7a52"
down_revision: str | Sequence[str] | None = "d1f60b8e4c73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACCESS_MODE_VALUES = ("CLOSED", "ON_APPROVAL", "OPEN")
_REQUEST_STATUS_VALUES = ("PENDING", "APPROVED", "REJECTED")
_ACCESS_MODE = sa.Enum(*_ACCESS_MODE_VALUES, name="accessmode")
_REQUEST_STATUS = sa.Enum(*_REQUEST_STATUS_VALUES, name="accessrequeststatus")


def upgrade() -> None:
    """Upgrade schema."""
    # Created up front rather than inline: add_column never emits CREATE TYPE, and create_table
    # would emit a second one for a type this migration already owns.
    bind = op.get_bind()
    _ACCESS_MODE.create(bind, checkfirst=True)
    _REQUEST_STATUS.create(bind, checkfirst=True)

    # The default is only there to fill the rows that already exist; it is dropped right after so
    # the column keeps taking its value from the Python side, like every other one in this schema.
    op.add_column(
        "instances",
        sa.Column(
            "access_mode",
            postgresql.ENUM(*_ACCESS_MODE_VALUES, name="accessmode", create_type=False),
            nullable=False,
            server_default="CLOSED",
        ),
    )
    op.alter_column("instances", "access_mode", server_default=None)

    op.create_table(
        "access_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(*_REQUEST_STATUS_VALUES, name="accessrequeststatus", create_type=False),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_access_requests_email"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("access_requests")
    op.drop_column("instances", "access_mode")
    bind = op.get_bind()
    _REQUEST_STATUS.drop(bind, checkfirst=True)
    _ACCESS_MODE.drop(bind, checkfirst=True)
