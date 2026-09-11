from collections.abc import Callable

from api.domain.article.models import Lang
from worker.domain.extraction.stemming_en import stem_en
from worker.domain.extraction.stemming_fr import stem_fr
from worker.domain.extraction.stemming_snowball import (
    ARABIC_TOKEN_RE,
    CYRILLIC_TOKEN_RE,
    LATIN_TOKEN_RE,
    make_snowball_stemmer,
)

stem_de = make_snowball_stemmer("german", LATIN_TOKEN_RE)
stem_es = make_snowball_stemmer("spanish", LATIN_TOKEN_RE)
stem_it = make_snowball_stemmer("italian", LATIN_TOKEN_RE)
stem_pt = make_snowball_stemmer("portuguese", LATIN_TOKEN_RE)
stem_ru = make_snowball_stemmer("russian", CYRILLIC_TOKEN_RE)
stem_ar = make_snowball_stemmer("arabic", ARABIC_TOKEN_RE)

_STEMMERS: dict[Lang, Callable[[str], list[str]]] = {
    Lang.FR: stem_fr,
    Lang.EN: stem_en,
    Lang.DE: stem_de,
    Lang.ES: stem_es,
    Lang.IT: stem_it,
    Lang.PT: stem_pt,
    Lang.RU: stem_ru,
    Lang.AR: stem_ar,
}


def stem_for_lang(lang: Lang, text: str) -> list[str] | None:
    """None means no stemmer covers `lang` (currently `Lang.ZH` and `Lang.MG`): callers must treat
    that as "keyword extraction is not possible for this text", not fall back to another
    language's stemming rules."""
    stemmer = _STEMMERS.get(lang)
    return stemmer(text) if stemmer is not None else None
