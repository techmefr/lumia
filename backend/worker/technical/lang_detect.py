from langdetect import DetectorFactory, LangDetectException, detect

from api.domain.article.models import Lang

# langdetect samples n-grams at random internally; without a fixed seed the same text can be
# classified differently across runs.
DetectorFactory.seed = 0

_DETECTED_CODE_TO_LANG: dict[str, Lang] = {
    "fr": Lang.FR,
    "en": Lang.EN,
    "de": Lang.DE,
    "es": Lang.ES,
    "it": Lang.IT,
    "pt": Lang.PT,
    "ru": Lang.RU,
    "ar": Lang.AR,
    "zh-cn": Lang.ZH,
    "zh-tw": Lang.ZH,
}


def detect_lang(text: str) -> Lang:
    """Malagasy has no signature langdetect was trained to recognize, so any text it cannot place
    among the other nine interface languages lands on `Lang.MG`, the one with no stemmer either:
    an honest "unclassified" bucket rather than a wrong guess spent on a stemmer for the wrong
    language.
    """
    try:
        code = detect(text)
    except LangDetectException:
        return Lang.MG
    return _DETECTED_CODE_TO_LANG.get(code, Lang.MG)
