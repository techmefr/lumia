import re

from nltk.stem.snowball import SnowballStemmer

_stemmer = SnowballStemmer("french")
_TOKEN_RE = re.compile(r"[a-zàâçéèêëîïôûùüÿñæœ]+")


def stem_fr(text: str) -> list[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    return [_stemmer.stem(token) for token in tokens]
