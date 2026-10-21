"""add export jobs

Revision ID: a9d41e7b3c60
Revises: a3e9b7d21c64
Create Date: 2026-10-21 11:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9d41e7b3c60"
down_revision: str | Sequence[str] | None = "a3e9b7d21c64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

export_kind = sa.Enum("PLAYLIST_EPUB", name="exportkind")
export_status = sa.Enum("PENDING", "READY", "FAILED", name="exportstatus")
export_kind_column = postgresql.ENUM("PLAYLIST_EPUB", name="exportkind", create_type=False)
export_status_column = postgresql.ENUM(
    "PENDING", "READY", "FAILED", name="exportstatus", create_type=False
)


def upgrade() -> None:
    """Upgrade schema."""
    export_kind.create(op.get_bind(), checkfirst=True)
    export_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", export_kind_column, nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("status", export_status_column, nullable=False),
        sa.Column("file_name", sa.String(), nullable=True),
        sa.Column("data", sa.LargeBinary(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_export_jobs_user_id"), "export_jobs", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_export_jobs_user_id"), table_name="export_jobs")
    op.drop_table("export_jobs")
    export_status.drop(op.get_bind(), checkfirst=True)
    export_kind.drop(op.get_bind(), checkfirst=True)
