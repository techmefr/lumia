import pytest

from api.domain.user.models import DigestFrequency, ReadingLang
from api.technical.email.digest_messages import DigestItem, render_digest_email
from api.technical.email.messages import EmailContent

_ITEMS = [
    DigestItem(
        title="Le <chat> & la souris",
        url="https://news.test/chat?a=1&b=2",
        source="Le Blog",
        summary="Une histoire courte.",
    ),
    DigestItem(
        title="No summary here", url="https://news.test/plain", source="Other", summary=None
    ),
]


def _render(language: str, frequency: DigestFrequency = DigestFrequency.DAILY) -> EmailContent:
    return render_digest_email(
        language=language,
        frequency=frequency,
        items=_ITEMS,
        settings_url="https://lumia.test/settings#digest",
    )


@pytest.mark.parametrize("language", [lang.value for lang in ReadingLang])
def test_every_reading_language_has_its_own_digest_wording(language: str) -> None:
    content = _render(language)
    english = _render("en")

    assert content.subject
    if language != "en":
        assert content.subject != english.subject


def test_an_unknown_language_falls_back_to_english() -> None:
    assert _render("xx").subject == _render("en").subject


def test_the_subject_says_which_period_the_digest_covers() -> None:
    daily = _render("fr", DigestFrequency.DAILY)
    weekly = _render("fr", DigestFrequency.WEEKLY)

    assert daily.subject != weekly.subject


def test_both_alternatives_carry_every_article_and_the_settings_link() -> None:
    content = _render("en")

    for item in _ITEMS:
        assert item.title in content.text_body
        assert item.url in content.text_body
        assert item.source in content.text_body
    assert "https://lumia.test/settings#digest" in content.text_body
    assert "settings#digest" in content.html_body
    assert "No summary here" in content.html_body


def test_the_html_escapes_titles_and_urls() -> None:
    content = _render("en")

    assert "<chat>" not in content.html_body
    assert "&lt;chat&gt;" in content.html_body
    assert "a=1&amp;b=2" in content.html_body


def test_the_mail_carries_no_image_and_so_no_tracking_pixel() -> None:
    content = _render("en")

    assert "<img" not in content.html_body
    assert "background-image" not in content.html_body
