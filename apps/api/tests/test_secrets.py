from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.core.secrets import CredentialError, decrypt_credential, encrypt_credential


def test_encrypt_credential_round_trips_without_persisting_plaintext() -> None:
    key = Fernet.generate_key().decode("ascii")
    secret = "nvapi-raw-secret-value"

    ciphertext = encrypt_credential(secret, key)

    assert secret not in ciphertext
    assert decrypt_credential(ciphertext, key) == secret


def test_decrypt_credential_rejects_wrong_key() -> None:
    ciphertext = encrypt_credential("nvapi-secret", Fernet.generate_key().decode("ascii"))

    with pytest.raises(CredentialError, match="cannot be decrypted"):
        decrypt_credential(ciphertext, Fernet.generate_key().decode("ascii"))


def test_encrypt_credential_requires_configured_key() -> None:
    with pytest.raises(CredentialError, match="CREDENTIAL_ENCRYPTION_KEY"):
        encrypt_credential("nvapi-secret", "")
