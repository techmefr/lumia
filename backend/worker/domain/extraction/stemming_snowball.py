import re
from collections.abc import Callable

from nltk.stem.snowball import SnowballStemmer

LATIN_TOKEN_RE = re.compile(r"[a-zàâäéèêëïîôöùûüÿçñãõáíóúāēīōūß]+")
CYRILLIC_TOKEN_RE = re.compile(r"[а-яё]+")
ARABIC_TOKEN_RE = re.compile(r"[ء-ي]+")


def make_snowball_stemmer(
    nltk_language: str, token_pattern: re.Pattern[str]
) -> Callable[[str], list[str]]:
    stemmer = SnowballStemmer(nltk_language)

    def stem(text: str) -> list[str]:
        tokens = token_pattern.findall(text.lower())
        return [stemmer.stem(token) for token in tokens]

    return stem
