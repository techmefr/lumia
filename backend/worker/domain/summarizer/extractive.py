import re

_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]")
_MIN_SIGNIFICANT_LENGTH = 20


def summarize_extractive(text: str, *, max_sentences: int = 3) -> str:
    sentences = [sentence.strip() for sentence in _SENTENCE_RE.findall(text)]
    significant = [sentence for sentence in sentences if len(sentence) >= _MIN_SIGNIFICANT_LENGTH]
    return " ".join(significant[:max_sentences])
