from api.technical.crypto.secret_box import decrypt_secret, encrypt_secret


def test_encrypt_then_decrypt_returns_the_original_secret() -> None:
    ciphertext = encrypt_secret("super-secret-client-secret")
    assert ciphertext != "super-secret-client-secret"
    assert decrypt_secret(ciphertext) == "super-secret-client-secret"
