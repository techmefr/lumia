"""widen the article and keyword language to the ten interface languages

Revision ID: 61a242bfadb8
Revises: e8b1c40d7a52
Create Date: 2026-09-11 09:36:01.011559

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "61a242bfadb8"
down_revision: str | Sequence[str] | None = "c2a6f81e934d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

old_lang = sa.Enum("FR", "EN", name="lang")
new_lang = sa.Enum("FR", "EN", "ES", "DE", "IT", "PT", "RU", "AR", "ZH", "MG", name="lang_wide")


def upgrade() -> None:
    """Upgrade schema.

    A stemmer now covers eight of the ten interface languages (see `stem_for_lang`), and an
    article or keyword can genuinely be in any of the ten, stemmed or not: the type widens to
    match, under a temporary name so the old two-value `lang` type can be dropped before the wide
    one takes its place.
    """
    new_lang.create(op.get_bind(), checkfirst=True)
    op.execute(
        "ALTER TABLE articles ALTER COLUMN original_lang "
        "TYPE lang_wide USING original_lang::text::lang_wide"
    )
    op.execute("ALTER TABLE keywords ALTER COLUMN lang TYPE lang_wide USING lang::text::lang_wide")
    old_lang.drop(op.get_bind(), checkfirst=True)
    op.execute("ALTER TYPE lang_wide RENAME TO lang")


def downgrade() -> None:
    """Downgrade schema.

    `keywords` is unique on (term, lang): clamping a keyword's language straight to FR could
    collide with a keyword that already exists in FR for the same term. Every `article_keywords`
    row pointing at the row that would collide is repointed at the surviving FR one first, the
    now-orphaned duplicate is dropped, and only then does the rest get clamped.
    """
    op.execute("ALTER TYPE lang RENAME TO lang_wide")
    old_lang.create(op.get_bind(), checkfirst=True)
    op.execute(
        "UPDATE article_keywords ak "
        "SET keyword_id = fr.id "
        "FROM keywords dup "
        "JOIN keywords fr ON fr.term = dup.term AND fr.lang = 'FR' AND fr.id <> dup.id "
        "WHERE ak.keyword_id = dup.id AND dup.lang NOT IN ('FR', 'EN')"
    )
    op.execute(
        "DELETE FROM keywords dup "
        "WHERE dup.lang NOT IN ('FR', 'EN') "
        "AND EXISTS ("
        "  SELECT 1 FROM keywords fr WHERE fr.term = dup.term AND fr.lang = 'FR' AND fr.id <> dup.id"
        ")"
    )
    op.execute("UPDATE keywords SET lang = 'FR' WHERE lang NOT IN ('FR', 'EN')")
    op.execute("UPDATE articles SET original_lang = 'FR' WHERE original_lang NOT IN ('FR', 'EN')")
    op.execute(
        "ALTER TABLE articles ALTER COLUMN original_lang TYPE lang USING original_lang::text::lang"
    )
    op.execute("ALTER TABLE keywords ALTER COLUMN lang TYPE lang USING lang::text::lang")
    new_lang.drop(op.get_bind(), checkfirst=True)
