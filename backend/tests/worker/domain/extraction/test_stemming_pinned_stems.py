"""Stemmed keywords feed relevance scoring, so a stemmer change silently reshuffles every
article's score. These expectations are pinned per language: if one breaks, the stemmer
behaviour moved and the scoring impact has to be assessed before the change lands."""

import pytest

from api.domain.article.models import Lang
from worker.domain.extraction.stemming import stem_for_lang

PINNED_STEMS: dict[Lang, tuple[str, list[str]]] = {
    Lang.FR: (
        "les chats mangent rapidement nationalement continuation",
        ["le", "chat", "mangent", "rapid", "national", "continu"],
    ),
    Lang.EN: (
        "the cats are running nationally organization happiness",
        ["the", "cat", "are", "run", "nation", "organ", "happi"],
    ),
    Lang.DE: (
        "die katzen laufen schnell möglichkeit freundschaft",
        ["die", "katz", "lauf", "schnell", "moglich", "freundschaft"],
    ),
    Lang.ES: (
        "los gatos corren rapidamente nacionalidad felicidad",
        ["los", "gat", "corr", "rapid", "nacional", "felic"],
    ),
    Lang.IT: (
        "i gatti corrono rapidamente nazionalita felicita",
        ["i", "gatt", "corr", "rapid", "nazional", "felic"],
    ),
    Lang.PT: (
        "os gatos correm rapidamente nacionalidade felicidade",
        ["os", "gat", "corr", "rapid", "nacional", "felic"],
    ),
    Lang.RU: (
        "кошки бегают быстро национальный счастье",
        ["кошк", "бега", "быстр", "национальн", "счаст"],
    ),
    Lang.AR: (
        "الكتاب كتب مدرسة المدينة طالب",
        ["كتاب", "كتب", "مدرس", "مدين", "طالب"],
    ),
}


@pytest.mark.parametrize("lang", list(PINNED_STEMS))
def test_stem_for_lang_matches_the_pinned_stems(lang: Lang) -> None:
    text, expected = PINNED_STEMS[lang]
    assert stem_for_lang(lang, text) == expected


def test_every_supported_language_is_pinned() -> None:
    unpinned = [
        lang
        for lang in Lang
        if stem_for_lang(lang, "test") is not None and lang not in PINNED_STEMS
    ]
    assert unpinned == []
