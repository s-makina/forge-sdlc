"""Execution event and artefact collection (subphase 3.7).

Captures execution events, tool calls, and commands into the event log, and
stores artefacts (test reports, patches, diffs) in object storage with a
database record pointing at the stored object (README §12.2, FR-5.3).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.events import ExecutionArtefact, ExecutionEvent
from app.storage.client import ObjectStore


def _next_sequence(db: Session, execution_id: str) -> int:
    max_seq = db.scalar(
        select(func.max(ExecutionEvent.sequence)).where(
            ExecutionEvent.execution_id == execution_id
        )
    )
    return (max_seq or 0) + 1


def record_event(
    db: Session,
    execution_id: str,
    kind: str,
    message: str,
    *,
    level: str = "info",
    details: str | None = None,
) -> ExecutionEvent:
    """Record a single execution event with an incrementing sequence."""
    event = ExecutionEvent(
        execution_id=execution_id,
        sequence=_next_sequence(db, execution_id),
        kind=kind,
        level=level,
        message=message,
        details=details,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def record_command(db: Session, execution_id: str, command: str, exit_code: int) -> ExecutionEvent:
    """Record a terminal/test command run."""
    return record_event(
        db,
        execution_id,
        kind="command",
        message=command,
        details=f"exit_code={exit_code}",
    )


def record_tool_call(db: Session, execution_id: str, tool: str, result: str) -> ExecutionEvent:
    """Record a coding-runtime tool call."""
    return record_event(
        db,
        execution_id,
        kind="tool_call",
        message=tool,
        details=result,
    )


def list_events(db: Session, execution_id: str) -> list[ExecutionEvent]:
    """Return all events for an execution in sequence order."""
    stmt = (
        select(ExecutionEvent)
        .where(ExecutionEvent.execution_id == execution_id)
        .order_by(ExecutionEvent.sequence)
    )
    return list(db.scalars(stmt).all())


def store_artefact(
    db: Session,
    store: ObjectStore,
    bucket: str,
    execution_id: str,
    name: str,
    data: bytes,
    *,
    kind: str | None = None,
    content_type: str | None = None,
) -> ExecutionArtefact:
    """Store an artefact in object storage and record a DB reference."""
    key = f"executions/{execution_id}/{name}"
    stored = store.put(bucket, key, data, content_type=content_type)
    artefact = ExecutionArtefact(
        execution_id=execution_id,
        name=name,
        location=f"{stored.bucket}/{stored.key}",
        size_bytes=stored.size_bytes,
        mime_type=content_type,
        kind=kind,
    )
    db.add(artefact)
    db.commit()
    db.refresh(artefact)
    return artefact


def list_artefacts(db: Session, execution_id: str) -> list[ExecutionArtefact]:
    """Return all stored artefacts for an execution."""
    stmt = (
        select(ExecutionArtefact)
        .where(ExecutionArtefact.execution_id == execution_id)
        .order_by(ExecutionArtefact.id)
    )
    return list(db.scalars(stmt).all())