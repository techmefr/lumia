from api.domain.article.models import Lang
from worker.domain.extraction.stemming import stem_for_lang


def test_stem_for_lang_collapses_german_inflected_forms_to_the_same_stem() -> None:
    stems_singular = stem_for_lang(Lang.DE, "Katze")
    stems_plural = stem_for_lang(Lang.DE, "Katzen")
    assert stems_singular is not None
    assert stems_plural is not None
    assert stems_singular[0] == stems_plural[0]


def test_stem_for_lang_collapses_spanish_inflected_forms_to_the_same_stem() -> None:
    stems_singular = stem_for_lang(Lang.ES, "gato")
    stems_plural = stem_for_lang(Lang.ES, "gatos")
    assert stems_singular is not None
    assert stems_plural is not None
    assert stems_singular[0] == stems_plural[0]


def test_stem_for_lang_collapses_italian_inflected_forms_to_the_same_stem() -> None:
    stems_singular = stem_for_lang(Lang.IT, "gatto")
    stems_plural = stem_for_lang(Lang.IT, "gatti")
    assert stems_singular is not None
    assert stems_plural is not None
    assert stems_singular[0] == stems_plural[0]


def test_stem_for_lang_collapses_portuguese_inflected_forms_to_the_same_stem() -> None:
    stems_singular = stem_for_lang(Lang.PT, "gato")
    stems_plural = stem_for_lang(Lang.PT, "gatos")
    assert stems_singular is not None
    assert stems_plural is not None
    assert stems_singular[0] == stems_plural[0]


def test_stem_for_lang_collapses_russian_inflected_forms_to_the_same_stem() -> None:
    stems_singular = stem_for_lang(Lang.RU, "кошка")
    stems_plural = stem_for_lang(Lang.RU, "кошки")
    assert stems_singular is not None
    assert stems_plural is not None
    assert stems_singular[0] == stems_plural[0]


def test_stem_for_lang_strips_the_arabic_definite_article() -> None:
    stems_with_article = stem_for_lang(Lang.AR, "الكتاب")
    stems_without_article = stem_for_lang(Lang.AR, "كتاب")
    assert stems_with_article is not None
    assert stems_without_article is not None
    assert stems_with_article[0] == stems_without_article[0]


def test_stem_for_lang_delegates_french_to_the_existing_stemmer() -> None:
    stems = stem_for_lang(Lang.FR, "Les Chats Mangent")
    assert stems is not None
    assert len(stems) == 3


def test_stem_for_lang_delegates_english_to_the_existing_stemmer() -> None:
    stems = stem_for_lang(Lang.EN, "The Cats Run")
    assert stems is not None
    assert len(stems) == 3


def test_stem_for_lang_returns_none_for_chinese_because_no_stemmer_covers_it() -> None:
    assert stem_for_lang(Lang.ZH, "这是一篇文章") is None


def test_stem_for_lang_returns_none_for_malagasy_because_no_stemmer_covers_it() -> None:
    assert stem_for_lang(Lang.MG, "Ity dia lahatsoratra iray") is None
