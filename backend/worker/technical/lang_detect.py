import re

_TOKEN_RE = re.compile(r"[a-zàâçéèêëîïôûùüÿñæœ]+")

_FR_MARKERS = {"le", "la", "les", "de", "des", "et", "un", "une", "est", "dans", "pour", "avec"}
_EN_MARKERS = {"the", "and", "of", "is", "in", "to", "for", "with", "that", "on", "as"}


def detect_lang(text: str) -> str:
    words = _TOKEN_RE.findall(text.lower())
    fr_score = sum(1 for word in words if word in _FR_MARKERS)
    en_score = sum(1 for word in words if word in _EN_MARKERS)
    return "fr" if fr_score > en_score else "en"
