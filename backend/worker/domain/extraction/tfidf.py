from sklearn.feature_extraction.text import TfidfVectorizer


def extract_keywords(tokens: list[str], *, top_n: int = 10) -> list[tuple[str, float]]:
    if not tokens:
        return []

    vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
    matrix = vectorizer.fit_transform([" ".join(tokens)])
    scores = matrix.toarray()[0]
    terms = vectorizer.get_feature_names_out()

    ranked = sorted(zip(terms, scores, strict=True), key=lambda pair: pair[1], reverse=True)
    return [(term, float(score)) for term, score in ranked[:top_n]]
