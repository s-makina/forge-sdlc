"""Permissive email type for local development.

Pydantic's built-in :class:`pydantic.EmailStr` delegates to ``email-validator``,
which rejects reserved / special-use domains (for example ``.local`` per RFC 6762).
ForgeSDLC runs locally with ``operator@forgesdlc.local`` as the bootstrap
operator account, so this type accepts those addresses while still rejecting
structurally invalid input.
"""

from __future__ import annotations

import re
from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import BeforeValidator

_LOCAL_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    try:
        return validate_email(value, check_deliverability=False).normalized
    except EmailNotValidError:
        # Reserved/special-use domains (e.g. .local) are acceptable locally;
        # fall back to a structural check so malformed input is still rejected.
        if not _LOCAL_EMAIL.match(value):
            raise ValueError("Invalid email address") from None
        return value


EmailStr = Annotated[str, BeforeValidator(_validate_email)]
