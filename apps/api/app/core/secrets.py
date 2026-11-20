"""Credential reference resolution.

Credentials are referenced indirectly (e.g. ``env:OPENAI_API_KEY``), never stored
inline. ``resolve_credential`` turns a reference into a secret value at call time.
The value must never be logged or returned by the API; ``redact`` is provided for
the rare places that need a safe placeholder.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class CredentialError(RuntimeError):
    """Raised when a credential reference is malformed or unset."""


@dataclass(frozen=True, slots=True)
class ResolvedCredential:
    reference: str
    value: str

    def __repr__(self) -> str:  # pragma: no cover - defensive
        return f"ResolvedCredential(reference={self.reference!r}, value=***)"


def resolve_credential(reference: str | None) -> str | None:
    """Resolve a credential reference to its secret value.

    Supported forms:
    - ``env:NAME`` -> the value of environment variable ``NAME``.
    - ``None`` / empty -> ``None`` (no credential; acceptable for local Ollama).
    """
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
