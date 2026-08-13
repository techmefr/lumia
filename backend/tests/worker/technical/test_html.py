from worker.technical.html import extract_first_image, strip_html


def test_strip_html_removes_tags_and_keeps_text() -> None:
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_collapses_whitespace_across_block_elements() -> None:
    assert strip_html("<p>Hello</p>\n<p>World</p>") == "Hello World"


def test_strip_html_of_plain_text_is_unchanged() -> None:
    assert strip_html("already plain") == "already plain"


def test_extract_first_image_returns_the_first_img_src() -> None:
    html = '<p>Text</p><img src="https://example.com/a.jpg"><img src="https://example.com/b.jpg">'
    assert extract_first_image(html) == "https://example.com/a.jpg"


def test_extract_first_image_returns_none_when_there_is_no_image() -> None:
    assert extract_first_image("<p>No image here</p>") is None


def test_extract_first_image_ignores_an_img_tag_with_no_src() -> None:
    html = '<img alt="broken"><img src="https://example.com/ok.jpg">'
    assert extract_first_image(html) == "https://example.com/ok.jpg"
