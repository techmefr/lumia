import re

from nltk.stem.snowball import SnowballStemmer

_stemmer = SnowballStemmer("english")
_TOKEN_RE = re.compile(r"[a-z]+")


def stem_en(text: str) -> list[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    return [_stemmer.stem(token) for token in tokens]
