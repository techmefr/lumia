"""add outbound webhooks and their deliveries

Revision ID: c4e8a2f61b93
Revises: c4b8e2a1d695
Create Date: 2026-10-21 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e8a2f61b93"
down_revision: str | Sequence[str] | None = "c4b8e2a1d695"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

delivery_status = sa.Enum("PENDING", "DELIVERED", "FAILED", name="deliverystatus")
delivery_status_column = postgresql.ENUM(
    "PENDING", "DELIVERED", "FAILED", name="deliverystatus", create_type=False
)


def upgrade() -> None:
    """Upgrade schema."""
    delivery_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "outbound_webhooks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("secret_encrypted", sa.String(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbound_webhooks_user_id", "outbound_webhooks", ["user_id"], unique=False)
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("webhook_id", sa.Uuid(), nullable=False),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", delivery_status_column, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["webhook_id"], ["outbound_webhooks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_webhook_deliveries_webhook_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
    op.drop_index("ix_outbound_webhooks_user_id", table_name="outbound_webhooks")
    op.drop_table("outbound_webhooks")
    delivery_status.drop(op.get_bind(), checkfirst=True)
