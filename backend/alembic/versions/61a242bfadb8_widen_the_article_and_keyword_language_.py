"""widen the article and keyword language to the ten interface languages

Revision ID: 61a242bfadb8
Revises: e8b1c40d7a52
Create Date: 2026-09-11 09:36:01.011559

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "61a242bfadb8"
down_revision: str | Sequence[str] | None = "c2a6f81e934d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

old_lang = sa.Enum("FR", "EN", name="lang")
new_lang = sa.Enum("FR", "EN", "ES", "DE", "IT", "PT", "RU", "AR", "ZH", "MG", name="lang_wide")

# Postgres ships a text-search configuration for eight of the ten languages; zh and mg have none,
# so they fall back to "simple", which indexes words without stemming rather than stemming them as
# if they were French. Every branch is immutable, which a generated column requires.
_REGCONFIG_BY_LANG = {
    "EN": "english",
    "ES": "spanish",
    "DE": "german",
    "IT": "italian",
    "PT": "portuguese",
    "RU": "russian",
    "AR": "arabic",
    "ZH": "simple",
    "MG": "simple",
}


def _search_vector_expression(regconfig_by_lang: dict[str, str], *, fallback: str) -> str:
    """The generated column's body: one branch per language, FR and the unknown sharing the last."""
    branches = "\n    ".join(
        f"WHEN '{lang}' THEN to_tsvector("
        f"'{regconfig}', title || ' ' || coalesce(summary, '') || ' ' || content)"
        for lang, regconfig in regconfig_by_lang.items()
    )
    return (
        "\nCASE original_lang\n    " + branches + f"\n    ELSE to_tsvector('{fallback}', "
        "title || ' ' || coalesce(summary, '') || ' ' || content)\nEND\n"
    )


def _create_search_vector(expression: str) -> None:
    """Puts the generated column and its index back once the type it reads has changed.

    Postgres refuses to alter the type of a column a generated column depends on, so the column
    goes away for the length of the type change and comes back computed from the new type.
    """
    op.add_column(
        "articles",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(expression, persisted=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_articles_search_vector",
        "articles",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def upgrade() -> None:
    """Upgrade schema.

    A stemmer now covers eight of the ten interface languages (see `stem_for_lang`), and an
    article or keyword can genuinely be in any of the ten, stemmed or not: the type widens to
    match, under a temporary name so the old two-value `lang` type can be dropped before the wide
    one takes its place.
    """
    op.drop_index("ix_articles_search_vector", table_name="articles")
    op.drop_column("articles", "search_vector")
    new_lang.create(op.get_bind(), checkfirst=True)
    op.execute(
        "ALTER TABLE articles ALTER COLUMN original_lang "
        "TYPE lang_wide USING original_lang::text::lang_wide"
    )
    op.execute("ALTER TABLE keywords ALTER COLUMN lang TYPE lang_wide USING lang::text::lang_wide")
    old_lang.drop(op.get_bind(), checkfirst=True)
    op.execute("ALTER TYPE lang_wide RENAME TO lang")
    _create_search_vector(_search_vector_expression(_REGCONFIG_BY_LANG, fallback="french"))


def downgrade() -> None:
    """Downgrade schema.

    `keywords` is unique on (term, lang): clamping a keyword's language straight to FR could
    collide with a keyword that already exists in FR for the same term. Every `article_keywords`
    row pointing at the row that would collide is repointed at the surviving FR one first, the
    now-orphaned duplicate is dropped, and only then does the rest get clamped.
    """
    op.drop_index("ix_articles_search_vector", table_name="articles")
    op.drop_column("articles", "search_vector")
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
    _create_search_vector(_search_vector_expression({"EN": "english"}, fallback="french"))
