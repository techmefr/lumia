from worker.domain.extraction.tfidf import extract_keywords


def test_extract_keywords_ranks_the_most_frequent_stem_first() -> None:
    tokens = ["chat", "chien", "chat", "chat", "chien"]
    ranked = extract_keywords(tokens)
    assert ranked[0][0] == "chat"
    assert ranked[0][1] > ranked[1][1]


def test_extract_keywords_respects_top_n() -> None:
    tokens = ["a", "b", "c", "d", "e"]
    ranked = extract_keywords(tokens, top_n=2)
    assert len(ranked) == 2


def test_extract_keywords_of_empty_tokens_is_empty() -> None:
    assert extract_keywords([]) == []
