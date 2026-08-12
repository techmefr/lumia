from worker.technical.html import strip_html


def test_strip_html_removes_tags_and_keeps_text() -> None:
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_collapses_whitespace_across_block_elements() -> None:
    assert strip_html("<p>Hello</p>\n<p>World</p>") == "Hello World"


def test_strip_html_of_plain_text_is_unchanged() -> None:
    assert strip_html("already plain") == "already plain"
