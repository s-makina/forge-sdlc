"""Parsing and validation of versioned YAML agent definitions (README 8.4).

A definition is validated in two layers:

1. **Structural** - the document must match :class:`AgentDefinition` (required
   fields, types, value patterns). This layer is pure and does not touch the DB.
2. **Registry** - capabilities, tools and skills must exist in the registries.
   This layer is enforced by the agent-registry service, which has DB access.

Keeping the structural layer pure makes it trivially testable and reusable by the
dashboard's import flow.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.schemas.agents import ValidationIssue, ValidationReport

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-_]*$")


class AgentDefinition(BaseModel):
    """A single ``agent:`` document as in README 8.4."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=32)
    role: str = Field(min_length=1, max_length=128)
    instructions: str = Field(min_length=1)
    capabilities: list[str] = []
    model_profile: str = Field(min_length=1, max_length=64)
    tools: list[str] = []
    permissions: dict[str, bool] = {}
    skills: list[str] = []
    quality_gates: list[str] = []

    @field_validator("id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        if not _ID_RE.fullmatch(value):
            raise ValueError("id must be lowercase alphanumeric with '-' or '_'")
        return value

    @field_validator("version")
    @classmethod
    def _check_version(cls, value: str) -> str:
        if not _SEMVER_RE.fullmatch(value):
            raise ValueError("version must be a semantic version like 1.0.0")
        return value

    @field_validator("capabilities", "tools", "skills")
    @classmethod
    def _dedupe(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


def canonical_json(definition: AgentDefinition) -> str:
    """Deterministic JSON for a definition, used to hash it."""
    return json.dumps(definition.model_dump(), sort_keys=True, separators=(",", ":"))


def definition_hash(definition: AgentDefinition) -> str:
    """SHA-256 of the canonical definition, used to detect no-op revisions."""
    return hashlib.sha256(canonical_json(definition).encode("utf-8")).hexdigest()


def parse_definition(document: str) -> tuple[AgentDefinition | None, ValidationReport, str | None]:
    """Parse a YAML document string into a validated definition.

    Returns ``(definition, report, canonical_json)`` where ``definition`` is
    ``None`` when ``report.valid`` is ``False``.
    """
    try:
        raw: Any = yaml.safe_load(document)
    except yaml.YAMLError as exc:
        return (
            None,
            ValidationReport(
                valid=False,
                errors=[ValidationIssue(path="yaml", message=f"invalid YAML: {exc}")],
            ),
            None,
        )

    if not isinstance(raw, dict):
        return (
            None,
            ValidationReport(
                valid=False,
                errors=[ValidationIssue(path="agent", message="document must be a mapping")],
            ),
            None,
        )

    errors: list[ValidationIssue] = []
    if set(raw) != {"agent"}:
        if "agent" not in raw:
            errors.append(ValidationIssue(path="agent", message="missing top-level 'agent' key"))
        else:
            extras = sorted(set(raw) - {"agent"})
            errors.append(
                ValidationIssue(path="agent", message=f"unexpected keys: {', '.join(extras)}")
            )
    if errors:
        return None, ValidationReport(valid=False, errors=errors), None

    body = raw["agent"]
    if not isinstance(body, dict):
        return (
            None,
            ValidationReport(
                valid=False,
                errors=[ValidationIssue(path="agent", message="'agent' must be a mapping")],
            ),
            None,
        )

    try:
        definition = AgentDefinition.model_validate(body)
    except ValidationError as exc:
        for error in exc.errors():
            loc = ".".join(str(part) for part in error["loc"])
            errors.append(ValidationIssue(path=f"agent.{loc}", message=error["msg"]))
        return None, ValidationReport(valid=False, errors=errors), None

    report = ValidationReport(valid=True, errors=[], warnings=[])
    return definition, report, canonical_json(definition)


def parse_definition_file(path: str) -> tuple[AgentDefinition | None, ValidationReport, str | None]:
    """Read and parse a YAML file; read errors are reported as validation errors."""
    try:
        with open(path, encoding="utf-8") as handle:
            document = handle.read()
    except OSError as exc:
        return (
            None,
            ValidationReport(
                valid=False, errors=[ValidationIssue(path="file", message=str(exc))]
            ),
            None,
        )
    return parse_definition(document)
