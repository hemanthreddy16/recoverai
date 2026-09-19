"""Bills & EMIs management router with AI payment risk prediction, scheduling, tracking & WhatsApp reminders."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bills import BillEmi, BillReminderLog, BillRiskHistory
from app.models.recovery import AuditLog, Notification
from app.models.users import Customer
from app.schemas.api import (
    BillEmiCreate,
    BillEmiOut,
    BillEmiSummary,
    BillEmiUpdate,
    BillReminderLogOut,
    BillRiskHistoryOut,
    EvaluateDispatchResultOut,
    ReminderSettingsOut,
    ReminderSettingsUpdate,
    ReminderTimelineStepOut,
    RiskSummary,
    SendWhatsAppRequest,
    UpcomingActionsOut,
)
from app.security import AuthUser, get_current_user, require_role
from app.services.bill_risk_engine import evaluate_bill
from app.services.smart_reminder_engine import SmartReminderEngine

router = APIRouter(prefix="/bills", tags=["bills"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _compute_days(due_date: datetime) -> tuple[int, int]:
    """Returns (days_remaining, days_overdue)."""
    now = _utcnow()
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)
    
    diff = due_date.date() - now.date()
    days = diff.days
    if days >= 0:
        return days, 0
    else:
        return 0, abs(days)


def _serialize_bill(bill: BillEmi) -> dict[str, Any]:
    days_rem, days_over = _compute_days(bill.due_date)
    return {
        "id": bill.id,
        "merchant_id": bill.merchant_id,
        "customer_id": bill.customer_id,
        "name": bill.name,
        "category": bill.category,
        "amount": bill.amount,
        "currency": bill.currency,
        "due_date": bill.due_date,
        "recurrence": bill.recurrence,
        "customer_name": bill.customer_name,
        "customer_phone": bill.customer_phone,
        "customer_email": bill.customer_email,
        "payment_link": bill.payment_link,
        "notes": bill.notes,
        "status": bill.status,
        "risk_score": bill.risk_score if bill.risk_score is not None else 15,
        "risk_level": bill.risk_level or "Low",
        "risk_reason": bill.risk_reason or "Standard recurring obligation",
        "risk_factors": bill.get_risk_factors(),
        "days_remaining": days_rem,
        "days_overdue": days_over,
        "last_evaluated_at": bill.last_evaluated_at,
        "paid_at": bill.paid_at,
        "created_at": bill.created_at,
        "updated_at": bill.updated_at,
        "reminder_logs": [
            {
                "id": log.id,
                "bill_id": log.bill_id,
                "stage": getattr(log, "stage", "normal") or "normal",
                "channel": log.channel or "whatsapp",
                "recipient_phone": log.recipient_phone,
                "message": log.message,
                "status": log.status or "delivered",
                "delivery_status": getattr(log, "delivery_status", "delivered") or "delivered",
                "customer_response": getattr(log, "customer_response", "pending") or "pending",
                "payment_status_after": getattr(log, "payment_status_after", "pending") or "pending",
                "scheduled_for": getattr(log, "scheduled_for", None),
                "sent_at": log.sent_at,
            }
            for log in (bill.reminder_logs or [])
        ],

        "risk_history": [
            {
                "id": rh.id,
                "bill_id": rh.bill_id,
                "risk_score": rh.risk_score,
                "risk_level": rh.risk_level,
                "risk_reason": rh.risk_reason,
                "factors": rh.get_factors(),
                "evaluated_at": rh.evaluated_at,
            }
            for rh in (bill.risk_history or [])
        ],
    }


@router.get("", response_model=list[BillEmiOut])
def list_bills(
    category: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    risk_level: str | None = Query(None),
    date_range: str | None = Query(None),  # today | 7days | month | overdue
    search: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Lists all bills and EMIs matching filters with AI risk predictions and dynamic days."""
    query = db.query(BillEmi).filter_by(merchant_id=user.merchant_id)

    if category and category != "all":
        query = query.filter(func.lower(BillEmi.category) == category.lower())

    if status_filter and status_filter != "all":
        query = query.filter(func.lower(BillEmi.status) == status_filter.lower())

    if risk_level and risk_level != "all":
        query = query.filter(func.lower(BillEmi.risk_level) == risk_level.lower())

    now = _utcnow()
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)

    if date_range == "today":
        query = query.filter(BillEmi.due_date >= today_start, BillEmi.due_date < today_end)
    elif date_range == "7days":
        seven_days_end = today_start + timedelta(days=8)
        query = query.filter(BillEmi.due_date >= today_start, BillEmi.due_date < seven_days_end)
    elif date_range == "month":
        month_end = today_start + timedelta(days=30)
        query = query.filter(BillEmi.due_date >= today_start, BillEmi.due_date <= month_end)
    elif date_range == "overdue":
        query = query.filter(BillEmi.due_date < today_start, BillEmi.status != "Paid")

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(BillEmi.name).like(term),
                func.lower(BillEmi.customer_name).like(term),
                func.lower(BillEmi.customer_phone).like(term),
                func.lower(BillEmi.category).like(term),
                func.lower(BillEmi.notes).like(term),
                func.lower(BillEmi.risk_reason).like(term),
            )
        )

    bills = query.order_by(BillEmi.due_date.asc()).offset(offset).limit(limit).all()
    return [_serialize_bill(b) for b in bills]


@router.get("/summary", response_model=BillEmiSummary)
def get_bills_summary(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Aggregates real-time metrics, AI risk summary, upcoming vs overdue, category breakdown, and monthly projection."""
    bills = db.query(BillEmi).filter_by(merchant_id=user.merchant_id).all()

    now = _utcnow()
    today_date = now.date()
    seven_days_date = today_date + timedelta(days=7)

    total_upcoming_count = 0
    total_amount_due = 0.0
    due_today_count = 0
    due_today_amount = 0.0
    due_7_days_count = 0
    due_7_days_amount = 0.0
    overdue_count = 0
    overdue_amount = 0.0
    paid_count = 0
    paid_amount = 0.0

    # Risk Summary Metrics
    high_risk_count = 0
    high_risk_amount = 0.0
    medium_risk_count = 0
    medium_risk_amount = 0.0
    low_risk_count = 0
    low_risk_amount = 0.0
    total_score = 0
    scored_bills_count = 0
    reason_map: dict[str, int] = {}

    cat_map: dict[str, dict[str, Any]] = {}
    month_map: dict[str, dict[str, float]] = {}

    for b in bills:
        due_d = b.due_date.date() if hasattr(b.due_date, "date") else b.due_date
        c_name = b.category or "Other"
        if c_name not in cat_map:
            cat_map[c_name] = {"category": c_name, "count": 0, "amount": 0.0, "overdue_amount": 0.0}

        cat_map[c_name]["count"] += 1
        cat_map[c_name]["amount"] += b.amount

        # Month key e.g. "Oct 2026"
        month_key = b.due_date.strftime("%b %Y")
        if month_key not in month_map:
            month_map[month_key] = {"due_amount": 0.0, "paid_amount": 0.0}

        if b.status == "Paid":
            paid_count += 1
            paid_amount += b.amount
            month_map[month_key]["paid_amount"] += b.amount
            low_risk_count += 1
            low_risk_amount += b.amount
        else:
            month_map[month_key]["due_amount"] += b.amount
            if b.status == "Overdue" or (due_d < today_date and b.status != "Paid"):
                overdue_count += 1
                overdue_amount += b.amount
                cat_map[c_name]["overdue_amount"] += b.amount
            else:
                total_upcoming_count += 1
                total_amount_due += b.amount

            if due_d == today_date:
                due_today_count += 1
                due_today_amount += b.amount

            if today_date <= due_d <= seven_days_date:
                due_7_days_count += 1
                due_7_days_amount += b.amount

            # Risk calculation
            r_level = (b.risk_level or "Low").capitalize()
            if r_level == "High":
                high_risk_count += 1
                high_risk_amount += b.amount
            elif r_level == "Medium":
                medium_risk_count += 1
                medium_risk_amount += b.amount
            else:
                low_risk_count += 1
                low_risk_amount += b.amount

            if b.risk_reason:
                reason_map[b.risk_reason] = reason_map.get(b.risk_reason, 0) + 1

        if b.risk_score is not None:
            total_score += b.risk_score
            scored_bills_count += 1

    category_breakdown = sorted(list(cat_map.values()), key=lambda x: x["amount"], reverse=True)
    monthly_trend = [
        {"month": k, "due_amount": v["due_amount"], "paid_amount": v["paid_amount"]}
        for k, v in month_map.items()
    ]

    top_reasons = [
        {"reason": k, "count": v}
        for k, v in sorted(reason_map.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    total_amount_at_risk = round(high_risk_amount + medium_risk_amount, 2)
    avg_score = round(total_score / scored_bills_count, 1) if scored_bills_count > 0 else 15.0

    return {
        "total_upcoming_count": total_upcoming_count,
        "total_amount_due": round(total_amount_due, 2),
        "due_today_count": due_today_count,
        "due_today_amount": round(due_today_amount, 2),
        "due_7_days_count": due_7_days_count,
        "due_7_days_amount": round(due_7_days_amount, 2),
        "overdue_count": overdue_count,
        "overdue_amount": round(overdue_amount, 2),
        "high_risk_count": high_risk_count,
        "high_risk_amount": round(high_risk_amount, 2),
        "paid_count": paid_count,
        "paid_amount": round(paid_amount, 2),
        "risk_summary": {
            "high_risk_count": high_risk_count,
            "high_risk_amount": round(high_risk_amount, 2),
            "medium_risk_count": medium_risk_count,
            "medium_risk_amount": round(medium_risk_amount, 2),
            "low_risk_count": low_risk_count,
            "low_risk_amount": round(low_risk_amount, 2),
            "total_amount_at_risk": total_amount_at_risk,
            "average_risk_score": avg_score,
            "top_risk_reasons": top_reasons,
        },
        "upcoming_vs_overdue": {
            "upcoming_amount": round(total_amount_due, 2),
            "upcoming_count": total_upcoming_count,
            "overdue_amount": round(overdue_amount, 2),
            "overdue_count": overdue_count,
            "paid_amount": round(paid_amount, 2),
            "paid_count": paid_count,
        },
        "category_breakdown": category_breakdown,
        "monthly_trend": monthly_trend,
    }


@router.post("", response_model=BillEmiOut, status_code=status.HTTP_201_CREATED)
def create_bill(
    body: BillEmiCreate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> dict[str, Any]:
    """Creates a new Bill/EMI obligation, auto-links Customer and runs AI risk prediction."""
    now = _utcnow()
    due_tz = body.due_date.replace(tzinfo=timezone.utc) if body.due_date.tzinfo is None else body.due_date

    # Initial status
    if body.status:
        init_status = body.status
    else:
        if due_tz.date() < now.date():
            init_status = "Overdue"
        elif due_tz.date() == now.date():
            init_status = "Due Today"
        else:
            init_status = "Upcoming"

    # Find or link Customer
    customer = (
        db.query(Customer)
        .filter_by(merchant_id=user.merchant_id, phone=body.customer_phone)
        .first()
    )
    if not customer and body.customer_name:
        customer = Customer(
            merchant_id=user.merchant_id,
            external_id=f"CUST-B-{int(_utcnow().timestamp())}",
            name=body.customer_name,
            email=body.customer_email or f"{body.customer_phone}@example.com",
            phone=body.customer_phone,
            clv=body.amount,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

    bill = BillEmi(
        merchant_id=user.merchant_id,
        customer_id=customer.id if customer else None,
        name=body.name,
        category=body.category,
        amount=body.amount,
        currency=body.currency,
        due_date=body.due_date,
        recurrence=body.recurrence,
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        customer_email=body.customer_email,
        payment_link=body.payment_link,
        notes=body.notes,
        status=init_status,
        risk_level="Low",
        risk_score=15,
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)

    # Evaluate AI risk
    evaluate_bill(db, bill, save_history=True)
    db.commit()
    db.refresh(bill)

    # Log audit entry
    audit = AuditLog(
        merchant_id=user.merchant_id,
        actor=user.email,
        action="create_bill_emi",
        entity_type="bill_emi",
        entity_id=bill.id,
    )
    audit.set_detail({
        "bill_id": bill.id,
        "name": bill.name,
        "amount": bill.amount,
        "risk_score": bill.risk_score,
        "risk_level": bill.risk_level,
        "risk_reason": bill.risk_reason,
    })
    db.add(audit)
    db.commit()

    return _serialize_bill(bill)


# ----------------- Smart Payment Reminder Engine Routes -----------------

@router.get("/reminders/settings", response_model=ReminderSettingsOut)
def get_reminder_settings(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> Any:
    """Retrieves merchant reminder configuration and quiet hours."""
    return SmartReminderEngine.get_or_create_settings(db, user.merchant_id)


@router.put("/reminders/settings", response_model=ReminderSettingsOut)
def update_reminder_settings(
    body: ReminderSettingsUpdate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> Any:
    """Updates reminder configuration preferences, frequency, channels, and quiet hours."""
    settings = SmartReminderEngine.get_or_create_settings(db, user.merchant_id)
    
    if body.reminders_enabled is not None:
        settings.reminders_enabled = body.reminders_enabled
    if body.frequency is not None:
        settings.frequency = body.frequency
    if body.max_reminders is not None:
        settings.max_reminders = body.max_reminders
    if body.preferred_channel is not None:
        settings.preferred_channel = body.preferred_channel
    if body.quiet_hours_enabled is not None:
        settings.quiet_hours_enabled = body.quiet_hours_enabled
    if body.quiet_hours_start is not None:
        settings.quiet_hours_start = body.quiet_hours_start
    if body.quiet_hours_end is not None:
        settings.quiet_hours_end = body.quiet_hours_end
    if body.risk_multiplier_enabled is not None:
        settings.risk_multiplier_enabled = body.risk_multiplier_enabled

    settings.updated_at = _utcnow()
    db.commit()
    db.refresh(settings)

    audit = AuditLog(
        merchant_id=user.merchant_id,
        actor=user.email,
        action="update_reminder_settings",
        entity_type="bill_reminder_settings",
        entity_id=settings.id,
    )
    audit.set_detail(body.model_dump(exclude_unset=True))
    db.add(audit)
    db.commit()

    return settings


@router.get("/reminders/upcoming-actions", response_model=UpcomingActionsOut)
def get_upcoming_reminder_actions(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Returns reminder engine metrics, statistics, and pending scheduled action queue."""
    return SmartReminderEngine.get_upcoming_actions(user.merchant_id, db)


@router.post("/reminders/evaluate-and-dispatch", response_model=EvaluateDispatchResultOut)
def evaluate_and_dispatch_reminders(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> dict[str, Any]:
    """Evaluates all merchant obligations and dispatches eligible pending reminders."""
    logs = SmartReminderEngine.dispatch_smart_reminders(user.merchant_id, db)
    return {
        "dispatched_count": len(logs),
        "dispatched_logs": [
            {
                "id": l.id,
                "bill_id": l.bill_id,
                "stage": l.stage,
                "channel": l.channel,
                "recipient_phone": l.recipient_phone,
                "message": l.message,
                "status": l.status,
                "delivery_status": l.delivery_status,
                "customer_response": l.customer_response,
                "payment_status_after": l.payment_status_after,
                "scheduled_for": l.scheduled_for,
                "sent_at": l.sent_at,
            }
            for l in logs
        ],
        "message": f"Successfully evaluated and dispatched {len(logs)} smart payment reminder(s).",
    }


@router.get("/{bill_id}/timeline", response_model=list[ReminderTimelineStepOut])
def get_bill_reminder_timeline(
    bill_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Generates the full visual communication & lifecycle timeline for a bill/EMI obligation."""
    bill = (
        db.query(BillEmi)
        .filter_by(id=bill_id, merchant_id=user.merchant_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Bill / EMI obligation not found")
    return SmartReminderEngine.build_reminder_timeline(bill, db)


@router.get("/{bill_id}", response_model=BillEmiOut)
def get_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:

    """Retrieves single bill/EMI detail with reminder and risk calculation history."""
    bill = (
        db.query(BillEmi)
        .filter_by(id=bill_id, merchant_id=user.merchant_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Bill / EMI obligation not found")
    return _serialize_bill(bill)


@router.post("/{bill_id}/recalculate-risk", response_model=BillEmiOut)
def recalculate_bill_risk(
    bill_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> dict[str, Any]:
    """Recalculates AI risk prediction for a bill obligation and appends to risk history."""
    bill = (
        db.query(BillEmi)
        .filter_by(id=bill_id, merchant_id=user.merchant_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Bill / EMI obligation not found")

    evaluate_bill(db, bill, save_history=True)
    db.commit()
    db.refresh(bill)

    return _serialize_bill(bill)


@router.post("/recalculate-all-risk")
def recalculate_all_bills_risk(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> dict[str, Any]:
    """Batch recalculates AI risk predictions for all active merchant obligations."""
    bills = db.query(BillEmi).filter_by(merchant_id=user.merchant_id).all()
    count = 0
    for b in bills:
        evaluate_bill(db, b, save_history=True)
        count += 1
    db.commit()

    return {
        "status": "success",
        "recalculated_count": count,
        "timestamp": _utcnow().isoformat(),
    }


@router.patch("/{bill_id}", response_model=BillEmiOut)
def update_bill(
    bill_id: int,
    body: BillEmiUpdate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> dict[str, Any]:
    """Updates bill information or status, triggering AI risk re-evaluation."""
    bill = (
        db.query(BillEmi)
        .filter_by(id=bill_id, merchant_id=user.merchant_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Bill / EMI obligation not found")

    data = body.model_dump(exclude_unset=True)
    for field, val in data.items():
        setattr(bill, field, val)

    if body.status == "Paid" and not bill.paid_at:
        bill.paid_at = _utcnow()
    elif body.status and body.status != "Paid":
        bill.paid_at = None

    bill.updated_at = _utcnow()
    db.commit()

    # Re-evaluate risk with new parameters
    evaluate_bill(db, bill, save_history=True)
    db.commit()
    db.refresh(bill)

    # Log audit entry
    audit = AuditLog(
        merchant_id=user.merchant_id,
        actor=user.email,
        action="update_bill_emi",
        entity_type="bill_emi",
        entity_id=bill.id,
    )
    audit.set_detail(data)
    db.add(audit)
    db.commit()

    return _serialize_bill(bill)


@router.post("/{bill_id}/mark-paid", response_model=BillEmiOut)
def mark_bill_paid(
    bill_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> dict[str, Any]:
    """Marks a bill/EMI as paid and updates risk to minimum."""
    bill = (
        db.query(BillEmi)
        .filter_by(id=bill_id, merchant_id=user.merchant_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Bill / EMI obligation not found")

    bill.status = "Paid"
    bill.paid_at = _utcnow()
    bill.risk_level = "Low"
    bill.risk_score = 5
    bill.risk_reason = "Obligation settled and marked as Paid"
    bill.set_risk_factors(["Payment successfully captured and settled"])
    bill.updated_at = _utcnow()
    db.commit()

    # Add risk history record for settlement
    history = BillRiskHistory(
        bill_id=bill.id,
        merchant_id=bill.merchant_id,
        risk_score=5,
        risk_level="Low",
        risk_reason="Obligation settled and marked as Paid",
        evaluated_at=_utcnow(),
    )
    history.set_factors(["Payment successfully captured and settled"])
    db.add(history)

    audit = AuditLog(
        merchant_id=user.merchant_id,
        actor=user.email,
        action="mark_bill_paid",
        entity_type="bill_emi",
        entity_id=bill.id,
    )
    audit.set_detail({"bill_id": bill.id, "amount": bill.amount, "paid_at": bill.paid_at.isoformat()})
    db.add(audit)
    db.commit()
    db.refresh(bill)

    return _serialize_bill(bill)


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> None:
    """Deletes a bill/EMI obligation and related logs."""
    bill = (
        db.query(BillEmi)
        .filter_by(id=bill_id, merchant_id=user.merchant_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Bill / EMI obligation not found")

    db.delete(bill)
    db.commit()

    audit = AuditLog(
        merchant_id=user.merchant_id,
        actor=user.email,
        action="delete_bill_emi",
        entity_type="bill_emi",
        entity_id=bill_id,
    )
    audit.set_detail({"deleted_bill_id": bill_id, "name": bill.name})
    db.add(audit)
    db.commit()


@router.post("/{bill_id}/send-whatsapp")
def send_whatsapp_reminder(
    bill_id: int,
    body: SendWhatsAppRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> dict[str, Any]:
    """Dispatches a formatted WhatsApp payment reminder and logs to communication history."""
    bill = (
        db.query(BillEmi)
        .filter_by(id=bill_id, merchant_id=user.merchant_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Bill / EMI obligation not found")

    due_str = bill.due_date.strftime("%d %b %Y")
    link = bill.payment_link or f"https://pay.resurge.dev/bill/{bill.id}"
    
    if body.custom_message and body.custom_message.strip():
        msg = body.custom_message.strip()
    else:
        msg = (
            f"Hello {bill.customer_name}, this is a reminder from Resurge regarding your "
            f"{bill.category} obligation '{bill.name}' of ₹{bill.amount:,.0f} due on {due_str}. "
        )
        if body.include_payment_link:
            msg += f"Please complete your payment securely at: {link}"

    # 1. Record in Notification table
    notif = Notification(
        merchant_id=user.merchant_id,
        customer_id=bill.customer_id,
        channel="whatsapp",
        subject=f"Bill Reminder: {bill.name}",
        body=msg,
        status="sent",
        sent_at=_utcnow(),
    )
    db.add(notif)

    # 2. Record in BillReminderLog
    log = BillReminderLog(
        bill_id=bill.id,
        merchant_id=user.merchant_id,
        channel="whatsapp",
        recipient_phone=bill.customer_phone,
        message=msg,
        status="sent",
        sent_at=_utcnow(),
    )
    db.add(log)

    # 3. Log AuditLog
    audit = AuditLog(
        merchant_id=user.merchant_id,
        actor=user.email,
        action="send_whatsapp_reminder",
        entity_type="bill_emi",
        entity_id=bill.id,
    )
    audit.set_detail({
        "bill_id": bill.id,
        "recipient": bill.customer_phone,
        "channel": "whatsapp",
        "notification_id": notif.id,
    })
    db.add(audit)
    db.commit()
    db.refresh(log)

    clean_phone = "".join([c for c in bill.customer_phone if c.isdigit()])
    if len(clean_phone) == 10:
        clean_phone = f"91{clean_phone}"
    wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"

    return {
        "status": "success",
        "message": "WhatsApp reminder dispatched and logged successfully",
        "log_id": log.id,
        "sent_at": log.sent_at.isoformat(),
        "recipient_phone": bill.customer_phone,
        "rendered_message": msg,
        "whatsapp_direct_url": wa_url,
    }
