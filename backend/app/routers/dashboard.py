"""Dashboard router: headline KPIs + recovery trend."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.payments import Payment
from app.models.recovery import RecoveryCase
from app.security import AuthUser, get_current_user
from app.schemas.api import DashboardMetrics

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardMetrics)
def dashboard(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)) -> DashboardMetrics:
    mid = user.merchant_id

    at_risk = (
        db.query(func.sum(RecoveryCase.amount_at_risk))
        .filter_by(merchant_id=mid, recovery_status="open").scalar() or 0.0
    )
    recovered = (
        db.query(func.sum(RecoveryCase.amount_recovered))
        .filter_by(merchant_id=mid, recovery_status="recovered").scalar() or 0.0
    )
    total = db.query(func.count(RecoveryCase.id)).filter_by(merchant_id=mid).scalar() or 0
    rec_count = db.query(func.count(RecoveryCase.id)).filter_by(merchant_id=mid, recovery_status="recovered").scalar() or 0
    active = db.query(func.count(RecoveryCase.id)).filter_by(merchant_id=mid, recovery_status="open").scalar() or 0
    failed_payments = db.query(func.count(Payment.id)).filter_by(merchant_id=mid, status="failed").scalar() or 0
    abandon = db.query(func.count(RecoveryCase.id)).filter_by(merchant_id=mid, event_type="checkout_abandoned").scalar() or 0
    sub_fail = db.query(func.count(RecoveryCase.id)).filter_by(merchant_id=mid, event_type="subscription_failed").scalar() or 0

    recovery_rate = (rec_count / total) if total else 0.0

    # Calculate predicted recoverable amount from open cases
    open_cases = db.query(RecoveryCase).filter_by(merchant_id=mid, recovery_status="open").all()
    predicted_recoverable = sum(
        (c.amount_at_risk or 0.0) * (c.recovery_probability if c.recovery_probability is not None else 0.5)
        for c in open_cases
    )

    # High risk cases (amount >= 10,000 or risk_score >= 0.7)
    high_risk_rows = (
        db.query(RecoveryCase)
        .filter_by(merchant_id=mid)
        .filter((RecoveryCase.amount_at_risk >= 10000) | (RecoveryCase.risk_score >= 0.6))
        .order_by(RecoveryCase.created_at.desc())
        .limit(5)
        .all()
    )
    high_risk_cases = [
        {
            "id": c.id,
            "customer_id": c.customer_id,
            "amount_at_risk": c.amount_at_risk,
            "event_type": c.event_type,
            "failure_reason": c.failure_reason,
            "risk_score": c.risk_score,
            "recovery_probability": c.recovery_probability,
            "policy_decision": c.policy_decision,
            "recovery_status": c.recovery_status,
        }
        for c in high_risk_rows
    ]
    high_risk_customers_count = len(set(c["customer_id"] for c in high_risk_cases))

    # 14-day trend of recovered revenue + new cases.
    since = datetime.now(timezone.utc) - timedelta(days=14)
    rows = (
        db.query(
            func.date(RecoveryCase.created_at),
            func.count(RecoveryCase.id),
            func.sum(RecoveryCase.amount_recovered),
        )
        .filter_by(merchant_id=mid)
        .filter(RecoveryCase.created_at >= since)
        .group_by(func.date(RecoveryCase.created_at))
        .all()
    )
    trend = [
        {"date": str(r[0]), "cases": r[1], "recovered": float(r[2] or 0.0)} for r in rows
    ]

    # Recent pipeline runs summary
    recent_runs = (
        db.query(RecoveryCase)
        .filter_by(merchant_id=mid)
        .order_by(RecoveryCase.created_at.desc())
        .limit(6)
        .all()
    )
    pipeline_runs = [
        {
            "case_id": c.id,
            "event_type": c.event_type,
            "amount": c.amount_at_risk,
            "diagnosis": c.diagnosis,
            "strategy": c.recommended_action,
            "policy": c.policy_decision,
            "status": c.recovery_status,
            "probability": c.recovery_probability,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in recent_runs
    ]

    return DashboardMetrics(
        revenue_at_risk=float(at_risk),
        revenue_recovered=float(recovered),
        recovery_rate=round(recovery_rate, 4),
        active_cases=int(active),
        failed_payments=int(failed_payments),
        checkout_abandonments=int(abandon),
        subscription_failures=int(sub_fail),
        predicted_recoverable=round(float(predicted_recoverable), 2),
        high_risk_customers_count=int(high_risk_customers_count),
        recovery_trend=trend,
        recent_pipeline_runs=pipeline_runs,
        high_risk_cases=high_risk_cases,
    )
