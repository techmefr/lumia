"""deduplicate articles by canonical url

Revision ID: d5c1a70e82b4
Revises: b2f6a934c5e1
Create Date: 2026-09-16 09:00:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op
from api.technical.net.canonical_url import canonical_url

# revision identifiers, used by Alembic.
revision: str = "d5c1a70e82b4"
down_revision: str | Sequence[str] | None = "b2f6a934c5e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BACKFILL_BATCH = 1000


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("articles", sa.Column("canonical_url", sa.String(), nullable=True))
    connection = op.get_bind()
    _backfill_canonical_urls(connection)
    _collapse_duplicates(connection)
    op.alter_column("articles", "canonical_url", nullable=False)
    op.create_index("ix_articles_canonical_url", "articles", ["canonical_url"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # The rows merged on the way up are gone for good; only the column comes back.
    op.drop_index("ix_articles_canonical_url", table_name="articles")
    op.drop_column("articles", "canonical_url")


def _backfill_canonical_urls(connection: sa.Connection) -> None:
    """Fills the new column in bounded batches rather than in one statement.

    The value cannot be computed in SQL — the rules live in python — so every row has to travel to
    the process and back; a populated instance holds more articles than that is worth reading into
    memory at once.
    """
    update = sa.text("UPDATE articles SET canonical_url = :canonical WHERE id = :id")
    last_id: Any = None
    while True:
        select_batch = sa.text(
            "SELECT id, url FROM articles "
            + ("WHERE id > :last_id " if last_id is not None else "")
            + "ORDER BY id LIMIT :limit"
        )
        parameters: dict[str, Any] = {"limit": _BACKFILL_BATCH}
        if last_id is not None:
            parameters["last_id"] = last_id
        rows = connection.execute(select_batch, parameters).all()
        if not rows:
            return
        for row in rows:
            connection.execute(update, {"canonical": canonical_url(row.url), "id": row.id})
        last_id = rows[-1].id


def _collapse_duplicates(connection: sa.Connection) -> None:
    """Merges the articles a reader already holds twice into the earliest published one.

    Reading state, feedback and playlist membership move over before the extra rows go: a reader
    who had read one of the two copies must not find the survivor unread.
    """
    connection.execute(
        sa.text("""
        CREATE TEMPORARY TABLE article_duplicates ON COMMIT DROP AS
        SELECT article.id AS loser_id, keeper.id AS keeper_id
        FROM articles AS article
        JOIN feeds AS feed ON feed.id = article.feed_id
        JOIN LATERAL (
            SELECT other.id
            FROM articles AS other
            JOIN feeds AS other_feed ON other_feed.id = other.feed_id
            WHERE other_feed.user_id = feed.user_id
              AND other.canonical_url = article.canonical_url
            ORDER BY other.published_at, other.created_at, other.id
            LIMIT 1
        ) AS keeper ON TRUE
        WHERE keeper.id <> article.id
        """)
    )

    connection.execute(
        sa.text("""
        UPDATE user_article_feedback AS keeper_feedback
        SET sentiment = COALESCE(keeper_feedback.sentiment, loser_feedback.sentiment),
            saved = keeper_feedback.saved OR loser_feedback.saved,
            favorite = keeper_feedback.favorite OR loser_feedback.favorite,
            read = keeper_feedback.read OR loser_feedback.read,
            scroll_progress = GREATEST(
                keeper_feedback.scroll_progress, loser_feedback.scroll_progress
            )
        FROM article_duplicates AS duplicate
        JOIN user_article_feedback AS loser_feedback
            ON loser_feedback.article_id = duplicate.loser_id
        WHERE keeper_feedback.article_id = duplicate.keeper_id
          AND keeper_feedback.user_id = loser_feedback.user_id
        """)
    )
    connection.execute(
        sa.text("""
        DELETE FROM user_article_feedback AS loser_feedback
        USING article_duplicates AS duplicate
        WHERE loser_feedback.article_id = duplicate.loser_id
          AND EXISTS (
              SELECT 1 FROM user_article_feedback AS keeper_feedback
              WHERE keeper_feedback.article_id = duplicate.keeper_id
                AND keeper_feedback.user_id = loser_feedback.user_id
          )
        """)
    )
    connection.execute(
        sa.text("""
        UPDATE user_article_feedback AS loser_feedback
        SET article_id = duplicate.keeper_id
        FROM article_duplicates AS duplicate
        WHERE loser_feedback.article_id = duplicate.loser_id
        """)
    )

    connection.execute(
        sa.text("""
        CREATE TEMPORARY TABLE playlists_to_renumber ON COMMIT DROP AS
        SELECT DISTINCT item.playlist_id
        FROM playlist_items AS item
        JOIN article_duplicates AS duplicate ON duplicate.loser_id = item.article_id
        """)
    )
    connection.execute(
        sa.text("""
        DELETE FROM playlist_items AS loser_item
        USING article_duplicates AS duplicate
        WHERE loser_item.article_id = duplicate.loser_id
          AND EXISTS (
              SELECT 1 FROM playlist_items AS keeper_item
              WHERE keeper_item.article_id = duplicate.keeper_id
                AND keeper_item.playlist_id = loser_item.playlist_id
          )
        """)
    )
    connection.execute(
        sa.text("""
        UPDATE playlist_items AS loser_item
        SET article_id = duplicate.keeper_id
        FROM article_duplicates AS duplicate
        WHERE loser_item.article_id = duplicate.loser_id
        """)
    )
    # Positions are a dense 0-based run; a playlist that lost a duplicate entry has a hole in it.
    connection.execute(
        sa.text("""
        UPDATE playlist_items AS item
        SET position = ranked.new_position
        FROM (
            SELECT playlist_id,
                   article_id,
                   ROW_NUMBER() OVER (PARTITION BY playlist_id ORDER BY position) - 1
                       AS new_position
            FROM playlist_items
            WHERE playlist_id IN (SELECT playlist_id FROM playlists_to_renumber)
        ) AS ranked
        WHERE item.playlist_id = ranked.playlist_id
          AND item.article_id = ranked.article_id
          AND item.position <> ranked.new_position
        """)
    )

    connection.execute(
        sa.text("""
        DELETE FROM article_keywords AS link
        USING article_duplicates AS duplicate
        WHERE link.article_id = duplicate.loser_id
        """)
    )
    connection.execute(
        sa.text("""
        DELETE FROM articles AS article
        USING article_duplicates AS duplicate
        WHERE article.id = duplicate.loser_id
        """)
    )
