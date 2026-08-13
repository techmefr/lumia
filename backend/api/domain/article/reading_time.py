from worker.technical.html import strip_html

_WORDS_PER_MINUTE = 200


def estimate_reading_minutes(content: str) -> int:
    """Rounds up to at least a minute: a card reading "0 min" is noise, not information."""
    word_count = len(strip_html(content).split())
    return max(1, round(word_count / _WORDS_PER_MINUTE))
