"""Settings router: merchant policy (guardrails) read/update."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.recovery import MerchantPolicy
from app.security import AuthUser, get_current_user, require_role
from app.schemas.api import PolicyUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/policy")
def get_policy(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)) -> dict:
    p = db.query(MerchantPolicy).filter_by(merchant_id=user.merchant_id).first()
    if not p:
        p = MerchantPolicy(merchant_id=user.merchant_id)
        db.add(p)
        db.commit()
        db.refresh(p)
    return {
        "automatic_threshold": p.automatic_threshold,
        "approval_threshold": p.approval_threshold,
        "retry_limit": p.retry_limit,
        "max_recovery_attempts": p.max_recovery_attempts,
        "high_value_threshold": p.high_value_threshold,
        "allow_auto_retry": p.allow_auto_retry,
        "allow_auto_payment_link": p.allow_auto_payment_link,
        "allow_auto_notification": p.allow_auto_notification,
        "notification_channels": p.get_channels(),
    }


@router.patch("/policy")
def update_policy(
    body: PolicyUpdate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> dict:
    p = db.query(MerchantPolicy).filter_by(merchant_id=user.merchant_id).first()
    if not p:
        p = MerchantPolicy(merchant_id=user.merchant_id)
        db.add(p)
        db.commit()
        db.refresh(p)
    data = body.model_dump(exclude_unset=True)
    if "notification_channels" in data and data["notification_channels"] is not None:
        p.set_channels(data["notification_channels"])
        data.pop("notification_channels")
    for k, v in data.items():
        if v is not None:
            setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return {
        "automatic_threshold": p.automatic_threshold,
        "approval_threshold": p.approval_threshold,
        "retry_limit": p.retry_limit,
        "max_recovery_attempts": p.max_recovery_attempts,
        "high_value_threshold": p.high_value_threshold,
        "allow_auto_retry": p.allow_auto_retry,
        "allow_auto_payment_link": p.allow_auto_payment_link,
        "allow_auto_notification": p.allow_auto_notification,
        "notification_channels": p.get_channels(),
    }
