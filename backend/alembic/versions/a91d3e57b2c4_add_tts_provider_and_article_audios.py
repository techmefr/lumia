"""add the speech provider settings and the synthesised audio cache

Revision ID: a91d3e57b2c4
Revises: a4d82f9e1b36
Create Date: 2026-10-21 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a91d3e57b2c4"
down_revision: str | Sequence[str] | None = "a4d82f9e1b36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

tts_provider = sa.Enum("OPENAI", "CUSTOM", name="ttsprovider")


def upgrade() -> None:
    """Upgrade schema."""
    tts_provider.create(op.get_bind(), checkfirst=True)
    op.add_column("users", sa.Column("tts_provider", tts_provider, nullable=True))
    op.add_column("users", sa.Column("tts_api_key_encrypted", sa.String(), nullable=True))
    op.add_column("users", sa.Column("tts_endpoint_url", sa.String(), nullable=True))
    op.add_column("users", sa.Column("tts_model", sa.String(), nullable=True))
    op.add_column("users", sa.Column("tts_voice", sa.String(), nullable=True))
    op.create_table(
        "article_audios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("voice_hash", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "article_id", "voice_hash", name="uq_article_audios_voice"),
    )
    op.create_index(op.f("ix_article_audios_article_id"), "article_audios", ["article_id"])
    op.create_index(op.f("ix_article_audios_user_id"), "article_audios", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_article_audios_user_id"), table_name="article_audios")
    op.drop_index(op.f("ix_article_audios_article_id"), table_name="article_audios")
    op.drop_table("article_audios")
    op.drop_column("users", "tts_voice")
    op.drop_column("users", "tts_model")
    op.drop_column("users", "tts_endpoint_url")
    op.drop_column("users", "tts_api_key_encrypted")
    op.drop_column("users", "tts_provider")
    tts_provider.drop(op.get_bind(), checkfirst=True)
