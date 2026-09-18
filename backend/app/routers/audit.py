"""Audit log router for tracking user and system actions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.recovery import AuditLog
from app.schemas.api import AuditLogOut
from app.security import AuthUser, get_current_user, require_role

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    actor: str | None = Query(None),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> list[AuditLog]:
    query = db.query(AuditLog).filter_by(merchant_id=user.merchant_id)
    if actor:
        query = query.filter_by(actor=actor)
    if action:
        query = query.filter_by(action=action)
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    return query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{audit_id}", response_model=AuditLogOut)
def get_audit_log(
    audit_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> AuditLog:
    log = (
        db.query(AuditLog)
        .filter_by(id=audit_id, merchant_id=user.merchant_id)
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="Audit log entry not found")
    return log
