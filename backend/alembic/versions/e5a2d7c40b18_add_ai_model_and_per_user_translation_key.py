"""add ai model and per-user translation key

Revision ID: e5a2d7c40b18
Revises: d3b8c6a19f47
Create Date: 2026-08-13 18:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5a2d7c40b18"
down_revision: str | Sequence[str] | None = "d3b8c6a19f47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

translation_provider = sa.Enum("DEEPL", name="translationprovider")


def upgrade() -> None:
    """Upgrade schema."""
    translation_provider.create(op.get_bind(), checkfirst=True)
    op.add_column("users", sa.Column("ai_model", sa.String(), nullable=True))
    op.add_column("users", sa.Column("translation_provider", translation_provider, nullable=True))
    op.add_column("users", sa.Column("translation_api_key_encrypted", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "translation_api_key_encrypted")
    op.drop_column("users", "translation_provider")
    op.drop_column("users", "ai_model")
    translation_provider.drop(op.get_bind(), checkfirst=True)
