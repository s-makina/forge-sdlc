"""Audit logging service."""

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    actor_id: int | None = None,
    actor_email: str | None = None,
    entity_id: str | None = None,
    details: str | None = None,
) -> AuditLog:
    """Write an audit log entry and commit it."""
    entry = AuditLog(
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
