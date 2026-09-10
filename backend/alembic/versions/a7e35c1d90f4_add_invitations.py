"""add invitations

Revision ID: a7e35c1d90f4
Revises: b4e17d80c9a2
Create Date: 2026-09-10 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7e35c1d90f4"
down_revision: str | Sequence[str] | None = "b4e17d80c9a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("instance_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        # The type already exists, created with users.role: reuse it rather than trying to
        # declare it a second time.
        sa.Column(
            "role",
            postgresql.ENUM("ADMIN", "MEMBER", name="role", create_type=False),
            nullable=False,
        ),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["instance_id"], ["instances.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_invitations_instance_id", "invitations", ["instance_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_invitations_instance_id", table_name="invitations")
    op.drop_table("invitations")
