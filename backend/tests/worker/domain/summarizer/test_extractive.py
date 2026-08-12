from worker.domain.summarizer.extractive import summarize_extractive

ARTICLE = (
    "This is the first significant sentence of the article. "
    "Here is a second meaningful sentence with more content. "
    "A third sentence adds even more detail to the story. "
    "A fourth sentence that should not make the summary."
)


def test_summarize_extractive_keeps_the_first_significant_sentences_in_order() -> None:
    summary = summarize_extractive(ARTICLE, max_sentences=2)
    assert summary == (
        "This is the first significant sentence of the article. "
        "Here is a second meaningful sentence with more content."
    )


def test_summarize_extractive_skips_very_short_sentences() -> None:
    text = "Ok. This is the first real sentence worth keeping in the summary. Yes."
    summary = summarize_extractive(text, max_sentences=1)
    assert summary == "This is the first real sentence worth keeping in the summary."


def test_summarize_extractive_of_empty_text_is_empty() -> None:
    assert summarize_extractive("") == ""
