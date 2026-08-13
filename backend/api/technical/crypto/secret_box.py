from functools import lru_cache

from cryptography.fernet import Fernet

from config.crypto import get_crypto_config


@lru_cache
def _fernet() -> Fernet:
    return Fernet(get_crypto_config().secret_encryption_key.encode())


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
