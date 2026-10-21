"""add playlist members and who added each item

Revision ID: b8e3a51c7d04
Revises: a9d41e7b3c60, b8c3e1f47a26
Create Date: 2026-10-21 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8e3a51c7d04"
down_revision: str | Sequence[str] | None = ("a9d41e7b3c60", "b8c3e1f47a26")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

member_role = sa.Enum("VIEWER", "EDITOR", name="memberrole")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "playlist_members",
        sa.Column("playlist_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", member_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("playlist_id", "user_id"),
    )
    op.create_index(op.f("ix_playlist_members_user_id"), "playlist_members", ["user_id"])
    op.add_column("playlist_items", sa.Column("added_by_user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_playlist_items_added_by_user_id_users",
        "playlist_items",
        "users",
        ["added_by_user_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_playlist_items_added_by_user_id_users", "playlist_items", type_="foreignkey"
    )
    op.drop_column("playlist_items", "added_by_user_id")
    op.drop_index(op.f("ix_playlist_members_user_id"), table_name="playlist_members")
    op.drop_table("playlist_members")
    member_role.drop(op.get_bind(), checkfirst=True)
