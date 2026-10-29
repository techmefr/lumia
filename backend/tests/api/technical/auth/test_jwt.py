from uuid import uuid4

import pytest

from api.technical.auth.jwt import InvalidAccessTokenError, create_access_token, decode_access_token


def test_decode_access_token_returns_the_user_id_it_was_created_with() -> None:
    user_id = uuid4()
    token = create_access_token(user_id)
    assert decode_access_token(token) == user_id


def test_decode_access_token_rejects_a_garbage_token() -> None:
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token("not-a-jwt")


def test_decode_access_token_rejects_a_token_signed_with_another_secret() -> None:
    import jwt as pyjwt

    forged = pyjwt.encode({"sub": str(uuid4())}, "another-secret", algorithm="HS256")
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(forged)


def test_decode_access_claims_carries_the_session_version() -> None:
    from api.technical.auth.jwt import decode_access_claims

    user_id = uuid4()
    claims = decode_access_claims(create_access_token(user_id, 7))
    assert claims.user_id == user_id
    assert claims.session_version == 7
