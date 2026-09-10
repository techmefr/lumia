from api.domain.user.models import ReadingLang
from api.technical.email.messages import FALLBACK_LANGUAGE, render_magic_link_email

URL = "https://lumia.example/login?magic_token=abc"


def test_magic_link_email_is_rendered_in_french_for_a_french_account() -> None:
    content = render_magic_link_email(language=ReadingLang.FR, magic_link_url=URL)

    assert content.subject == "Votre lien de connexion Lumia"
    assert "vous connecter" in content.text_body


def test_magic_link_email_is_rendered_in_english_for_an_english_account() -> None:
    content = render_magic_link_email(language=ReadingLang.EN, magic_link_url=URL)

    assert content.subject == "Your Lumia sign-in link"
    assert "sign in" in content.text_body.lower()


def test_magic_link_email_falls_back_to_english_for_an_untranslated_language() -> None:
    fallback = render_magic_link_email(language=ReadingLang.MG, magic_link_url=URL)
    english = render_magic_link_email(language=FALLBACK_LANGUAGE, magic_link_url=URL)

    assert fallback == english


def test_magic_link_email_falls_back_to_english_for_an_unknown_language() -> None:
    content = render_magic_link_email(language="klingon", magic_link_url=URL)

    assert content.subject == "Your Lumia sign-in link"


def test_every_reading_language_renders_readable_text_rather_than_a_key() -> None:
    for language in ReadingLang:
        content = render_magic_link_email(language=language, magic_link_url=URL)

        assert content.subject
        assert "magic_link" not in content.subject
        assert URL in content.text_body
        assert f'href="{URL}"' in content.html_body


def test_magic_link_url_is_escaped_in_the_html_body() -> None:
    content = render_magic_link_email(
        language=ReadingLang.EN,
        magic_link_url='https://lumia.example/login?magic_token="><script>',
    )

    assert "<script>" not in content.html_body
    assert "&lt;script&gt;" in content.html_body


def test_translated_languages_have_their_own_subject() -> None:
    subjects = {
        language: render_magic_link_email(language=language, magic_link_url=URL).subject
        for language in (
            ReadingLang.FR,
            ReadingLang.EN,
            ReadingLang.ES,
            ReadingLang.DE,
            ReadingLang.IT,
            ReadingLang.PT,
        )
    }

    assert len(set(subjects.values())) == len(subjects)
