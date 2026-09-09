from api.domain.article.reading_time import estimate_reading_minutes


def test_a_short_article_still_reports_one_minute() -> None:
    assert estimate_reading_minutes("<p>Trois mots seulement</p>") == 1


def test_two_hundred_words_is_one_minute() -> None:
    assert estimate_reading_minutes(" ".join(["mot"] * 200)) == 1


def test_word_count_ignores_the_markup() -> None:
    words = " ".join(["mot"] * 400)
    plain = estimate_reading_minutes(words)
    wrapped = estimate_reading_minutes(f'<div class="entry-content"><p>{words}</p></div>')
    assert plain == wrapped == 2


def test_an_empty_article_reports_one_minute() -> None:
    assert estimate_reading_minutes("") == 1
