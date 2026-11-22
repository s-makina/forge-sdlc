"""Credential encryption and legacy environment-reference resolution.

Raw provider credentials are encrypted at rest and never returned by the API.
Legacy ``env:NAME`` references remain supported for existing installations.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken


class CredentialError(RuntimeError):
    """Raised when a credential reference is malformed, unset or cannot be decrypted."""


def _fernet(key: str) -> Fernet:
    normalized = key.strip()
    if not normalized:
        raise CredentialError("CREDENTIAL_ENCRYPTION_KEY is not configured")
    try:
        if len(normalized) == 64:
            normalized = base64.urlsafe_b64encode(bytes.fromhex(normalized)).decode("ascii")
        return Fernet(normalized.encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise CredentialError(
            "CREDENTIAL_ENCRYPTION_KEY must be a Fernet key or 32-byte hex value"
        ) from exc


def encrypt_credential(value: str, key: str) -> str:
    """Encrypt a provider API key before storing it in the database."""
    if not value.strip():
        raise CredentialError("API key cannot be empty")
    return _fernet(key).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_credential(ciphertext: str, key: str) -> str:
    """Decrypt a stored provider API key at the point of use."""
    try:
        return _fernet(key).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise CredentialError("Stored provider credential cannot be decrypted") from exc


@dataclass(frozen=True, slots=True)
class ResolvedCredential:
    reference: str
    value: str

    def __repr__(self) -> str:  # pragma: no cover - defensive
        return f"ResolvedCredential(reference={self.reference!r}, value=***)"


def resolve_credential(reference: str | None) -> str | None:
    """Resolve a legacy environment reference to its secret value."""
    if reference is None:
        return None
    ref = reference.strip()
    if not ref:
        return None
    scheme, _, target = ref.partition(":")
    if scheme != "env" or not target:
        raise CredentialError(
            f"Unsupported credential reference {ref!r}; use the 'env:NAME' form"
        )
    value = os.environ.get(target)
    if value is None:
        raise CredentialError(f"Credential reference {ref!r} is not set in the environment")
    return value


def redact(reference: str | None) -> str | None:
    """Return the credential reference's scheme with the secret name masked."""
    if reference is None:
        return None
    scheme, sep, _ = reference.partition(":")
    if not sep:
        return "***"
    return f"{scheme}:***"
