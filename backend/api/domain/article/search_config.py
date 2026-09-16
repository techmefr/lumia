"""Which postgres text-search configuration indexes and parses each article language.

Both sides of the search have to agree on this mapping. An article's `search_vector` is generated
under the configuration of its own `original_lang`, and the reader's query text has to be parsed
under those same configurations or it produces stems that nothing in the index carries.
"""

FALLBACK_REGCONFIG = "french"

# Postgres ships a text-search configuration for eight of the ten interface languages; zh and mg
# have none, so they fall back to "simple", which keeps words as they are rather than stemming
# them as if they belonged to another language.
REGCONFIG_BY_LANG = {
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

# FR reaches its configuration through the CASE fallback rather than a branch of its own, so it is
# absent from the mapping above and has to be added back here. Deduplicated because zh and mg share
# "simple", and ordered so the generated SQL is stable from one run to the next.
SEARCH_REGCONFIGS = tuple(dict.fromkeys([FALLBACK_REGCONFIG, *REGCONFIG_BY_LANG.values()]))


def search_vector_expression() -> str:
    """The body of the generated `search_vector` column: one branch per language.

    Every branch is immutable, which a generated column requires. Migrations keep their own frozen
    copy of the expression they applied; this one is what the current schema declares.
    """
    document = "title || ' ' || coalesce(summary, '') || ' ' || content"
    branches = " ".join(
        f"WHEN '{lang}' THEN to_tsvector('{regconfig}', {document})"
        for lang, regconfig in REGCONFIG_BY_LANG.items()
    )
    fallback = f"to_tsvector('{FALLBACK_REGCONFIG}', {document})"
    return f"CASE original_lang {branches} ELSE {fallback} END"
