"""one manual feed per user

Revision ID: e1b7d4c92a60
Revises: d5a7c3e9f201
Create Date: 2026-10-29 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e1b7d4c92a60"
down_revision: str | Sequence[str] | None = "d5a7c3e9f201"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX = "uq_feeds_one_manual_per_user"


def upgrade() -> None:
    """Upgrade schema."""
    _merge_duplicate_manual_feeds(op.get_bind())
    op.create_index(
        _INDEX,
        "feeds",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("source_type = 'MANUAL'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(_INDEX, table_name="feeds", postgresql_where=sa.text("source_type = 'MANUAL'"))


def _merge_duplicate_manual_feeds(connection: sa.Connection) -> None:
    connection.execute(
        sa.text("""
        CREATE TEMPORARY TABLE manual_feed_duplicates ON COMMIT DROP AS
        SELECT feed.id AS loser_id, keeper.id AS keeper_id
        FROM feeds AS feed
        JOIN LATERAL (
            SELECT other.id
            FROM feeds AS other
            WHERE other.user_id = feed.user_id AND other.source_type = 'MANUAL'
            ORDER BY other.created_at, other.id
            LIMIT 1
        ) AS keeper ON TRUE
        WHERE feed.source_type = 'MANUAL' AND keeper.id <> feed.id
        """)
    )
    connection.execute(
        sa.text("""
        UPDATE articles AS article
        SET feed_id = duplicate.keeper_id
        FROM manual_feed_duplicates AS duplicate
        WHERE article.feed_id = duplicate.loser_id
        """)
    )
    connection.execute(
        sa.text("""
        UPDATE saved_searches AS search
        SET feed_id = duplicate.keeper_id
        FROM manual_feed_duplicates AS duplicate
        WHERE search.feed_id = duplicate.loser_id
        """)
    )
    connection.execute(
        sa.text("""
        UPDATE user_feed_scores AS score
        SET score = GREATEST(score.score, loser.score)
        FROM manual_feed_duplicates AS duplicate
        JOIN user_feed_scores AS loser ON loser.feed_id = duplicate.loser_id
        WHERE score.feed_id = duplicate.keeper_id AND score.user_id = loser.user_id
        """)
    )
    connection.execute(
        sa.text("""
        DELETE FROM user_feed_scores AS loser
        USING manual_feed_duplicates AS duplicate
        WHERE loser.feed_id = duplicate.loser_id
          AND EXISTS (
              SELECT 1 FROM user_feed_scores AS kept
              WHERE kept.feed_id = duplicate.keeper_id AND kept.user_id = loser.user_id
          )
        """)
    )
    connection.execute(
        sa.text("""
        UPDATE user_feed_scores AS loser
        SET feed_id = duplicate.keeper_id
        FROM manual_feed_duplicates AS duplicate
        WHERE loser.feed_id = duplicate.loser_id
        """)
    )
    connection.execute(
        sa.text("""
        DELETE FROM feeds AS feed
        USING manual_feed_duplicates AS duplicate
        WHERE feed.id = duplicate.loser_id
        """)
    )
