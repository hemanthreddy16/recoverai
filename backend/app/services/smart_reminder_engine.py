"""Smart Payment Reminder Engine for RecoverAI.

Orchestrates multi-channel, risk-adjusted payment reminders with anti-spam protections,
quiet-hours compliance, delivery/response lifecycle tracking, and visual timeline synthesis.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.bills import BillEmi, BillReminderLog, BillReminderSettings
from app.services.bill_risk_engine import BillRiskEngine

logger = logging.getLogger("recoverai.reminders")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# =====================================================================
# 1. Multi-Channel Dispatcher Simulation / Sandbox
# =====================================================================

class ChannelProvider:
    """Base notification delivery provider."""

    @classmethod
    def send(cls, channel: str, recipient: str, message: str, payment_link: str | None = None) -> dict[str, str]:
        """Simulates transmission to recipient over chosen gateway with sandbox reliability."""
        logger.info(f"[{channel.upper()}] Sent to {recipient}: {message[:60]}... (Link: {payment_link})")
        return {
            "status": "delivered",
            "delivery_status": "delivered",
            "customer_response": "pending",
        }


class WhatsAppProvider(ChannelProvider):
    @classmethod
    def send_template(cls, phone: str, bill_name: str, amount: float, due_date: str, link: str | None) -> dict[str, str]:
        msg = f"Hello, reminder for your {bill_name} payment of ₹{amount:,.0f} due on {due_date}. Pay securely: {link or 'https://pay.recoverai.io'}"
        return cls.send("whatsapp", phone, msg, link)


class EmailProvider(ChannelProvider):
    @classmethod
    def send_email(cls, email: str, bill_name: str, amount: float, due_date: str, link: str | None) -> dict[str, str]:
        msg = f"Official Reminder: Your {bill_name} invoice of ₹{amount:,.0f} is due on {due_date}. Payment link: {link or 'https://pay.recoverai.io'}"
        return cls.send("email", email, msg, link)


class SMSProvider(ChannelProvider):
    @classmethod
    def send_sms(cls, phone: str, bill_name: str, amount: float, due_date: str, link: str | None) -> dict[str, str]:
        msg = f"RecoverAI: ₹{amount:,.0f} due on {due_date} for {bill_name}. Pay now: {link or 'https://pay.recoverai.io'}"
        return cls.send("sms", phone, msg, link)


# =====================================================================
# 2. Smart Reminder Engine Core
# =====================================================================

@dataclass
class ReminderCandidate:
    bill: BillEmi
    stage: str
    channel: str
    scheduled_for: datetime
    message: str
    reason: str
    priority: str  # low | medium | high | urgent


class SmartReminderEngine:
    """Evaluates upcoming obligations and schedules appropriate reminder stages."""

    STAGES_ORDER = ["7-day", "3-day", "1-day", "due_today", "overdue", "recovery"]

    @classmethod
    def get_or_create_settings(cls, db: Session, merchant_id: int) -> BillReminderSettings:
        """Retrieves or creates default reminder configuration for a merchant."""
        settings = db.query(BillReminderSettings).filter_by(merchant_id=merchant_id).first()
        if not settings:
            settings = BillReminderSettings(
                merchant_id=merchant_id,
                reminders_enabled=True,
                frequency="smart",
                max_reminders=4,
                preferred_channel="whatsapp",
                quiet_hours_enabled=True,
                quiet_hours_start="22:00",
                quiet_hours_end="08:00",
                risk_multiplier_enabled=True,
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    @classmethod
    def is_in_quiet_hours(cls, settings: BillReminderSettings, dt: datetime | None = None) -> bool:
        """Checks if the given time falls within the configured quiet hours window (handles overnight wraps)."""
        if not settings.quiet_hours_enabled:
            return False

        check_dt = dt or _utcnow()
        t = check_dt.time()

        try:
            sh, sm = map(int, settings.quiet_hours_start.split(":"))
            eh, em = map(int, settings.quiet_hours_end.split(":"))
            start_time = time(sh, sm)
            end_time = time(eh, em)
        except Exception:
            start_time = time(22, 0)
            end_time = time(8, 0)

        if start_time <= end_time:
            return start_time <= t <= end_time
        else:
            # Overnight wrap (e.g. 22:00 to 08:00)
            return t >= start_time or t <= end_time

    @classmethod
    def get_next_active_hour(cls, settings: BillReminderSettings, dt: datetime | None = None) -> datetime:
        """Returns the next valid timestamp when quiet hours end."""
        check_dt = dt or _utcnow()
        if not cls.is_in_quiet_hours(settings, check_dt):
            return check_dt

        try:
            eh, em = map(int, settings.quiet_hours_end.split(":"))
        except Exception:
            eh, em = 8, 0

        target = check_dt.replace(hour=eh, minute=em, second=0, microsecond=0)
        if target <= check_dt:
            target += timedelta(days=1)
        return target

    @classmethod
    def format_reminder_message(cls, bill: BillEmi, stage: str) -> str:
        """Generates tailored message templates for different stages."""
        due_str = bill.due_date.strftime("%d %b %Y")
        amt_str = f"₹{bill.amount:,.0f}"

        if stage == "7-day":
            return f"Hi {bill.customer_name}, this is a gentle advance reminder that your {bill.name} payment of {amt_str} is due on {due_str}. Pay easily at {bill.payment_link or 'https://pay.recoverai.io'}."
        elif stage == "3-day":
            return f"Hello {bill.customer_name}, your {bill.name} obligation of {amt_str} is due in 3 days on {due_str}. Tap here to complete payment: {bill.payment_link or 'https://pay.recoverai.io'}."
        elif stage == "1-day":
            return f"Important Reminder: {bill.customer_name}, your {bill.name} payment of {amt_str} is due tomorrow ({due_str}). Please pay now to avoid late penalties: {bill.payment_link or 'https://pay.recoverai.io'}."
        elif stage == "due_today":
            return f"Payment Due Today: Hi {bill.customer_name}, your {bill.name} amount {amt_str} is due today. Complete your instant payment: {bill.payment_link or 'https://pay.recoverai.io'}."
        elif stage == "overdue":
            return f"Action Required: {bill.customer_name}, your {bill.name} payment of {amt_str} was due on {due_str} and is now overdue. Please clear this obligation immediately: {bill.payment_link or 'https://pay.recoverai.io'}."
        elif stage == "recovery":
            return f"URGENT Recovery Alert: {bill.customer_name}, your {bill.name} payment of {amt_str} has failed or is severely overdue. Avoid service disruption by settling now: {bill.payment_link or 'https://pay.recoverai.io'}."
        else:
            return f"Reminder: {bill.name} payment of {amt_str} due on {due_str}. Payment link: {bill.payment_link or 'https://pay.recoverai.io'}."

    @classmethod
    def evaluate_bill_schedule(
        cls,
        bill: BillEmi,
        settings: BillReminderSettings,
        db: Session,
        now: datetime | None = None,
    ) -> ReminderCandidate | None:
        """Determines if a bill is currently due for a smart reminder stage."""
        if not settings.reminders_enabled:
            return None

        # Settle state check
        if bill.status in ["Paid", "Cancelled"]:
            return None

        now = now or _utcnow()
        due_d = bill.due_date.replace(tzinfo=timezone.utc) if bill.due_date.tzinfo is None else bill.due_date
        diff_days = (due_d.date() - now.date()).days

        # Ensure risk score is evaluated
        if bill.risk_score is None:
            BillRiskEngine.evaluate(db, bill, save_history=False)

        # Existing reminder logs for this bill
        existing_logs = db.query(BillReminderLog).filter_by(bill_id=bill.id).order_by(BillReminderLog.sent_at.desc()).all()
        sent_stages = {log.stage for log in existing_logs}
        total_sent = len(existing_logs)

        # Anti-spam: check max reminders
        if total_sent >= settings.max_reminders:
            return None

        # Anti-spam: check cooldown (at least 18 hours since last reminder unless severe recovery)
        if existing_logs:
            last_sent = existing_logs[0].sent_at
            if last_sent.tzinfo is None:
                last_sent = last_sent.replace(tzinfo=timezone.utc)
            hours_since_last = (now - last_sent).total_seconds() / 3600.0
            if hours_since_last < 18 and diff_days >= 0:
                # Too soon for another pre-due reminder
                return None

        # Determine target stage & priority based on timing and risk
        target_stage: str | None = None
        priority = "medium"
        reason = ""

        # Overdue / Recovery logic
        if diff_days < 0 or bill.status == "Overdue" or bill.status == "Failed":
            days_past = abs(diff_days)
            if days_past >= 3 or bill.status == "Failed" or bill.risk_score >= 71:
                if "recovery" not in sent_stages:
                    target_stage = "recovery"
                    priority = "urgent"
                    reason = f"Payment is {days_past} days overdue with high risk ({bill.risk_score}/100)"
                elif "overdue" not in sent_stages:
                    target_stage = "overdue"
                    priority = "high"
                    reason = f"Payment is {days_past} days past due date"
            else:
                if "overdue" not in sent_stages:
                    target_stage = "overdue"
                    priority = "high"
                    reason = f"Payment became overdue on {bill.due_date.strftime('%d %b')}"

        # Due Today logic
        elif diff_days == 0 or bill.status == "Due Today":
            if "due_today" not in sent_stages:
                target_stage = "due_today"
                priority = "high"
                reason = "Payment due date is today"

        # 1 Day Before
        elif diff_days == 1:
            if "1-day" not in sent_stages:
                target_stage = "1-day"
                priority = "high" if bill.risk_score >= 50 else "medium"
                reason = "Due date is tomorrow"

        # 3 Days Before
        elif diff_days <= 3:
            if "3-day" not in sent_stages:
                # Conservative mode only sends 3-day if risk >= 30
                if settings.frequency == "conservative" and bill.risk_score < 30:
                    target_stage = None
                else:
                    target_stage = "3-day"
                    priority = "medium"
                    reason = f"Due in {diff_days} days"

        # 7 Days Before (Optional / Smart)
        elif diff_days <= 7:
            if "7-day" not in sent_stages:
                # Smart rule: 7-day is sent if risk is medium/high or aggressive mode
                if settings.frequency == "aggressive" or (settings.risk_multiplier_enabled and bill.risk_score >= 31):
                    target_stage = "7-day"
                    priority = "low" if bill.risk_score <= 40 else "medium"
                    reason = f"Proactive 7-day notice (AI Risk: {bill.risk_level} - {bill.risk_score}/100)"

        if not target_stage:
            return None

        # Preferred channel selection
        channel = settings.preferred_channel
        if channel == "multi":
            channel = "whatsapp" if bill.customer_phone else "email"

        # Quiet hours scheduling
        sched_time = now
        if cls.is_in_quiet_hours(settings, now):
            sched_time = cls.get_next_active_hour(settings, now)

        message = cls.format_reminder_message(bill, target_stage)

        return ReminderCandidate(
            bill=bill,
            stage=target_stage,
            channel=channel,
            scheduled_for=sched_time,
            message=message,
            reason=reason,
            priority=priority,
        )

    @classmethod
    def get_upcoming_actions(cls, merchant_id: int, db: Session) -> dict[str, Any]:
        """Calculates reminder engine statistics and returns scheduled action queue for merchant."""
        settings = cls.get_or_create_settings(db, merchant_id)
        now = _utcnow()

        bills = db.query(BillEmi).filter_by(merchant_id=merchant_id).all()
        all_logs = db.query(BillReminderLog).filter_by(merchant_id=merchant_id).all()

        sent_count = sum(1 for l in all_logs if l.delivery_status in ["sent", "delivered", "opened"])
        failed_count = sum(1 for l in all_logs if l.delivery_status == "failed")
        recovered_logs = [l for l in all_logs if l.payment_status_after == "settled" or l.customer_response == "paid"]
        recovered_count = len(recovered_logs)

        # Recovered amount from bills that were paid after reminders
        recovered_amount = sum(
            b.amount for b in bills if b.status == "Paid" and any(l.bill_id == b.id for l in all_logs)
        )

        # Build candidate queue
        queue: list[dict[str, Any]] = []
        for b in bills:
            candidate = cls.evaluate_bill_schedule(b, settings, db, now)
            if candidate:
                queue.append({
                    "bill_id": b.id,
                    "bill_name": b.name,
                    "customer_name": b.customer_name,
                    "customer_phone": b.customer_phone,
                    "amount": b.amount,
                    "due_date": b.due_date.isoformat(),
                    "stage": candidate.stage,
                    "channel": candidate.channel,
                    "priority": candidate.priority,
                    "reason": candidate.reason,
                    "scheduled_for": candidate.scheduled_for.isoformat(),
                    "risk_score": b.risk_score,
                    "risk_level": b.risk_level,
                })

        # Sort queue by priority (urgent > high > medium > low) and scheduled_for
        priority_weights = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
        queue.sort(key=lambda x: (-priority_weights.get(x["priority"], 0), x["scheduled_for"]))

        next_action_time = queue[0]["scheduled_for"] if queue else None

        return {
            "reminders_enabled": settings.reminders_enabled,
            "scheduled_count": len(queue),
            "sent_count": sent_count,
            "failed_count": failed_count,
            "recovered_count": recovered_count,
            "recovered_amount": recovered_amount,
            "next_action_time": next_action_time,
            "queue": queue,
        }

    @classmethod
    def dispatch_smart_reminders(cls, merchant_id: int, db: Session, max_batch: int = 50) -> list[BillReminderLog]:
        """Dispatches all eligible scheduled reminders for a merchant and logs outcomes."""
        settings = cls.get_or_create_settings(db, merchant_id)
        if not settings.reminders_enabled:
            return []

        now = _utcnow()
        # If currently in quiet hours, do not dispatch immediately
        if cls.is_in_quiet_hours(settings, now):
            logger.info("Skipping immediate dispatch during quiet hours.")
            return []

        bills = db.query(BillEmi).filter_by(merchant_id=merchant_id).all()
        created_logs: list[BillReminderLog] = []

        for bill in bills:
            if len(created_logs) >= max_batch:
                break

            candidate = cls.evaluate_bill_schedule(bill, settings, db, now)
            if not candidate:
                continue

            # Execute channel provider dispatch
            resp = ChannelProvider.send(
                channel=candidate.channel,
                recipient=bill.customer_phone if candidate.channel in ["whatsapp", "sms"] else (bill.customer_email or bill.customer_phone),
                message=candidate.message,
                payment_link=bill.payment_link,
            )

            log = BillReminderLog(
                bill_id=bill.id,
                merchant_id=merchant_id,
                stage=candidate.stage,
                channel=candidate.channel,
                recipient_phone=bill.customer_phone,
                message=candidate.message,
                status=resp.get("status", "delivered"),
                delivery_status=resp.get("delivery_status", "delivered"),
                customer_response=resp.get("customer_response", "pending"),
                payment_status_after="pending",
                scheduled_for=candidate.scheduled_for,
                sent_at=now,
            )
            db.add(log)
            created_logs.append(log)

        if created_logs:
            db.commit()

        return created_logs

    @classmethod
    def build_reminder_timeline(cls, bill: BillEmi, db: Session) -> list[dict[str, Any]]:
        """Synthesizes the complete lifecycle visual timeline for a bill / EMI obligation."""
        timeline: list[dict[str, Any]] = []

        # 1. Creation step
        timeline.append({
            "id": "step_created",
            "title": "Payment Obligation Created",
            "description": f"Added to system with due date {bill.due_date.strftime('%d %b %Y')}",
            "stage": "creation",
            "timestamp": bill.created_at.isoformat() if bill.created_at else _utcnow().isoformat(),
            "channel": "system",
            "status": "completed",
            "icon": "plus-circle",
        })

        # 2. Risk Evaluation step
        risk_time = bill.last_evaluated_at or bill.created_at or _utcnow()
        timeline.append({
            "id": "step_risk_evaluated",
            "title": f"AI Risk Assessed ({bill.risk_level} Risk - {bill.risk_score}/100)",
            "description": bill.risk_reason or "Automated risk factor assessment computed",
            "stage": "risk_assessment",
            "timestamp": risk_time.isoformat(),
            "channel": "ai_engine",
            "status": "completed",
            "icon": "shield-alert" if bill.risk_level == "High" else "shield-check",
        })

        # 3. Reminder communication logs
        logs = db.query(BillReminderLog).filter_by(bill_id=bill.id).order_by(BillReminderLog.sent_at.asc()).all()
        for idx, l in enumerate(logs):
            title = f"{l.stage.replace('_', ' ').capitalize()} Reminder"
            desc = f"Sent via {l.channel.upper()} to {l.recipient_phone}. Status: {l.delivery_status}"
            if l.customer_response and l.customer_response != "pending":
                desc += f" (Customer {l.customer_response.replace('_', ' ')})"

            timeline.append({
                "id": f"step_log_{l.id}",
                "title": title,
                "description": desc,
                "stage": l.stage,
                "timestamp": l.sent_at.isoformat() if l.sent_at else _utcnow().isoformat(),
                "channel": l.channel,
                "status": "completed" if l.delivery_status in ["delivered", "opened", "sent"] else "failed",
                "customer_response": l.customer_response,
                "icon": "message-square",
            })

        # 4. Next scheduled step or final outcome
        if bill.status == "Paid":
            settled_time = bill.paid_at or bill.updated_at or _utcnow()
            timeline.append({
                "id": "step_settled",
                "title": "Payment Settled Successfully",
                "description": f"₹{bill.amount:,.0f} obligation fully recovered and marked as Paid",
                "stage": "settlement",
                "timestamp": settled_time.isoformat(),
                "channel": "gateway",
                "status": "completed",
                "icon": "check-circle-2",
            })
        elif bill.status == "Overdue":
            timeline.append({
                "id": "step_overdue_action",
                "title": "Active Recovery Workflow",
                "description": "Payment past deadline. Escalated automated multi-channel sequence active",
                "stage": "recovery",
                "timestamp": _utcnow().isoformat(),
                "channel": "recovery_agent",
                "status": "active",
                "icon": "alert-triangle",
            })
        else:
            # Check what next scheduled stage would be
            settings = cls.get_or_create_settings(db, bill.merchant_id)
            candidate = cls.evaluate_bill_schedule(bill, settings, db)
            if candidate:
                timeline.append({
                    "id": "step_scheduled_next",
                    "title": f"Next: {candidate.stage.replace('_', ' ').capitalize()} Reminder",
                    "description": f"Scheduled for {candidate.scheduled_for.strftime('%d %b, %H:%M')} via {candidate.channel.upper()}",
                    "stage": candidate.stage,
                    "timestamp": candidate.scheduled_for.isoformat(),
                    "channel": candidate.channel,
                    "status": "pending",
                    "icon": "clock",
                })
            else:
                timeline.append({
                    "id": "step_awaiting_due",
                    "title": "Awaiting Due Date",
                    "description": f"Standard monitoring until due date ({bill.due_date.strftime('%d %b %Y')})",
                    "stage": "monitoring",
                    "timestamp": bill.due_date.isoformat(),
                    "channel": "system",
                    "status": "pending",
                    "icon": "calendar",
                })

        return timeline
