"""enforce unique feeds and emails, and bind magic links to a purpose

Revision ID: b2c5d8e01f32
Revises: a1b4c7d90e21
Create Date: 2026-10-29 09:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import Connection

from alembic import op

revision: str = "b2c5d8e01f32"
down_revision: str | Sequence[str] | None = "a1b4c7d90e21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PURPOSE = sa.Enum("SIGN_IN", "PASSWORD_RESET", name="magiclinkpurpose")

_DEDUPLICATED_EMAIL = """
    CASE
        WHEN ranked.rank = 1 THEN ranked.lowered
        ELSE split_part(ranked.lowered, '@', 1) || '+duplicate' || ranked.rank
             || '@' || substr(ranked.lowered, strpos(ranked.lowered, '@') + 1)
    END
"""

_FEED_MERGE_STATEMENTS = (
    """
    CREATE TEMPORARY TABLE feed_merge ON COMMIT DROP AS
    SELECT id AS loser_id,
           first_value(id) OVER (
               PARTITION BY user_id, source_type, external_feed_id
               ORDER BY created_at, id
           ) AS keeper_id
    FROM feeds
    """,
    "DELETE FROM feed_merge WHERE loser_id = keeper_id",
    """
    UPDATE articles SET feed_id = m.keeper_id
    FROM feed_merge m WHERE articles.feed_id = m.loser_id
    """,
    """
    UPDATE saved_searches SET feed_id = m.keeper_id
    FROM feed_merge m WHERE saved_searches.feed_id = m.loser_id
    """,
    """
    DELETE FROM user_feed_scores s USING feed_merge m
    WHERE s.feed_id = m.loser_id
      AND EXISTS (
          SELECT 1 FROM user_feed_scores k
          WHERE k.user_id = s.user_id AND k.feed_id = m.keeper_id
      )
    """,
    """
    UPDATE user_feed_scores SET feed_id = m.keeper_id
    FROM feed_merge m WHERE user_feed_scores.feed_id = m.loser_id
    """,
    "DELETE FROM feeds USING feed_merge m WHERE feeds.id = m.loser_id",
)


def _merge_duplicate_feeds(connection: Connection) -> None:
    for statement in _FEED_MERGE_STATEMENTS:
        connection.execute(sa.text(statement))


def _lowercase_emails(connection: Connection) -> None:
    connection.execute(
        sa.text(
            f"""
            WITH ranked AS (
                SELECT id,
                       lower(email) AS lowered,
                       row_number() OVER (
                           PARTITION BY lower(email) ORDER BY created_at, id
                       ) AS rank
                FROM users
            )
            UPDATE users SET email = {_DEDUPLICATED_EMAIL}
            FROM ranked
            WHERE users.id = ranked.id AND users.email <> {_DEDUPLICATED_EMAIL}
            """
        )
    )
    connection.execute(
        sa.text("UPDATE invitations SET email = lower(email) WHERE email <> lower(email)")
    )
    connection.execute(
        sa.text(
            """
            DELETE FROM access_requests a USING access_requests b
            WHERE lower(a.email) = lower(b.email)
              AND (a.created_at, a.id) > (b.created_at, b.id)
            """
        )
    )
    connection.execute(
        sa.text("UPDATE access_requests SET email = lower(email) WHERE email <> lower(email)")
    )


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()
    _merge_duplicate_feeds(connection)
    op.create_unique_constraint(
        "uq_feeds_user_source_external", "feeds", ["user_id", "source_type", "external_feed_id"]
    )

    _lowercase_emails(connection)
    op.execute("CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email))")

    PURPOSE.create(connection, checkfirst=True)
    op.add_column(
        "magic_link_tokens",
        sa.Column("purpose", PURPOSE, nullable=False, server_default="SIGN_IN"),
    )
    op.alter_column("magic_link_tokens", "purpose", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("magic_link_tokens", "purpose")
    PURPOSE.drop(op.get_bind(), checkfirst=True)
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_constraint("uq_feeds_user_source_external", "feeds", type_="unique")
