"""Audit log routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps.auth import require_user
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogList, AuditLogRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditLogList)
def list_audit_logs(
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> AuditLogList:
    entries = list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)).all())
    total = int(db.scalar(select(func.count()).select_from(AuditLog)) or 0)
    return AuditLogList(items=[AuditLogRead.model_validate(e) for e in entries], total=total)
