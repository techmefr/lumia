"""widen the reading language to the ten interface languages

Revision ID: b4e17d80c9a2
Revises: f7c3b91a02de
Create Date: 2026-08-14 11:05:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b4e17d80c9a2'
down_revision: str | Sequence[str] | None = 'f7c3b91a02de'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

reading_lang = sa.Enum(
    'FR', 'EN', 'ES', 'DE', 'IT', 'PT', 'RU', 'AR', 'ZH', 'MG', name='readinglang'
)
lang = sa.Enum('FR', 'EN', name='lang')


def upgrade() -> None:
    """Upgrade schema.

    A type of its own rather than new values on `lang`: that one is the language an article was
    written in, bounded by the languages the keyword extractor has a stemmer for. The two names
    happen to overlap on FR and EN, which is why the cast below goes through text.
    """
    reading_lang.create(op.get_bind(), checkfirst=True)
    op.execute(
        'ALTER TABLE users ALTER COLUMN preferred_language '
        'TYPE readinglang USING preferred_language::text::readinglang'
    )


def downgrade() -> None:
    """Downgrade schema.

    Rows on a language `lang` does not have fall back to FR: the column is not nullable, and there
    is no honest narrower value for them.
    """
    op.execute(
        "UPDATE users SET preferred_language = 'FR' "
        "WHERE preferred_language NOT IN ('FR', 'EN')"
    )
    op.execute(
        'ALTER TABLE users ALTER COLUMN preferred_language '
        'TYPE lang USING preferred_language::text::lang'
    )
    reading_lang.drop(op.get_bind(), checkfirst=True)
