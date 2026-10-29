"""one article per canonical url in a feed

Revision ID: f4d9a1b73c82
Revises: e1b7d4c92a60
Create Date: 2026-10-29 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f4d9a1b73c82"
down_revision: str | Sequence[str] | None = "e1b7d4c92a60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX = "uq_articles_feed_canonical_url"

_UNIQUE_PER_ARTICLE = (
    ("article_tags", ("tag_id",)),
    ("article_keywords", ("keyword_id",)),
    ("article_audios", ("user_id", "voice_hash")),
    ("alert_notifications", ("saved_search_id",)),
)
_PLAIN_REFERENCES = ("chat_messages", "highlights", "article_shares")


def upgrade() -> None:
    """Upgrade schema."""
    _merge_duplicate_articles(op.get_bind())
    with op.get_context().autocommit_block():
        op.create_index(
            _INDEX,
            "articles",
            ["feed_id", "canonical_url"],
            unique=True,
            postgresql_concurrently=True,
            if_not_exists=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.get_context().autocommit_block():
        op.drop_index(_INDEX, table_name="articles", postgresql_concurrently=True, if_exists=True)


def _merge_duplicate_articles(connection: sa.Connection) -> None:
    connection.execute(
        sa.text("""
        CREATE TEMPORARY TABLE article_feed_duplicates ON COMMIT DROP AS
        SELECT article.id AS loser_id, keeper.id AS keeper_id
        FROM articles AS article
        JOIN LATERAL (
            SELECT other.id
            FROM articles AS other
            WHERE other.feed_id = article.feed_id
              AND other.canonical_url = article.canonical_url
            ORDER BY other.published_at, other.created_at, other.id
            LIMIT 1
        ) AS keeper ON TRUE
        WHERE keeper.id <> article.id
        """)
    )
    _merge_feedback(connection)
    _merge_playlist_items(connection)
    for table, key_columns in _UNIQUE_PER_ARTICLE:
        _move_unique_rows(connection, table, key_columns)
    for table in _PLAIN_REFERENCES:
        connection.execute(
            sa.text(f"""
            UPDATE {table} AS reference
            SET article_id = duplicate.keeper_id
            FROM article_feed_duplicates AS duplicate
            WHERE reference.article_id = duplicate.loser_id
            """)
        )
    connection.execute(
        sa.text("""
        DELETE FROM articles AS article
        USING article_feed_duplicates AS duplicate
        WHERE article.id = duplicate.loser_id
        """)
    )


def _move_unique_rows(connection: sa.Connection, table: str, key_columns: tuple[str, ...]) -> None:
    same_key = " AND ".join(f"kept.{column} = loser.{column}" for column in key_columns)
    connection.execute(
        sa.text(f"""
        DELETE FROM {table} AS loser
        USING article_feed_duplicates AS duplicate
        WHERE loser.article_id = duplicate.loser_id
          AND EXISTS (
              SELECT 1 FROM {table} AS kept
              WHERE kept.article_id = duplicate.keeper_id AND {same_key}
          )
        """)
    )
    connection.execute(
        sa.text(f"""
        UPDATE {table} AS loser
        SET article_id = duplicate.keeper_id
        FROM article_feed_duplicates AS duplicate
        WHERE loser.article_id = duplicate.loser_id
        """)
    )


def _merge_feedback(connection: sa.Connection) -> None:
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
        FROM article_feed_duplicates AS duplicate
        JOIN user_article_feedback AS loser_feedback
            ON loser_feedback.article_id = duplicate.loser_id
        WHERE keeper_feedback.article_id = duplicate.keeper_id
          AND keeper_feedback.user_id = loser_feedback.user_id
        """)
    )
    _move_unique_rows(connection, "user_article_feedback", ("user_id",))


def _merge_playlist_items(connection: sa.Connection) -> None:
    connection.execute(
        sa.text("""
        CREATE TEMPORARY TABLE playlists_to_renumber ON COMMIT DROP AS
        SELECT DISTINCT item.playlist_id
        FROM playlist_items AS item
        JOIN article_feed_duplicates AS duplicate ON duplicate.loser_id = item.article_id
        """)
    )
    _move_unique_rows(connection, "playlist_items", ("playlist_id",))
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
