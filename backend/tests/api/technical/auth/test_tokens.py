from api.technical.auth.tokens import generate_opaque_token, hash_token


def test_generate_opaque_token_returns_distinct_high_entropy_tokens() -> None:
    first = generate_opaque_token()
    second = generate_opaque_token()
    assert first != second
    assert len(first) >= 32


def test_hash_token_is_deterministic_and_one_way() -> None:
    token = generate_opaque_token()
    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != token
