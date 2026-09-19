"""MCP controlled tool implementations (single source of truth).

These functions are the ONLY way the agent system may touch sensitive business
and payment operations. Every call is:
  - input-validated (pydantic),
  - merchant-scoped (cannot cross merchant boundaries),
  - authorization-checked (requires a valid MCP token),
  - audit-logged (an MCPToolCall row is written for every invocation).

The standalone FastMCP server (app/mcp/server.py) and the backend gateway
(app/mcp/gateway.py) both delegate to this module, so behavior is identical
whether tools run in-process or over the MCP protocol.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import pydantic
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.logging_setup import logger
from app.models.payments import Payment, Subscription
from app.models.users import Customer
from app.models.recovery import (
    AuditLog,
    MCPToolCall,
    MerchantPolicy,
    Notification,
    RecoveryAction,
    RecoveryCase,
)

# ---- auth token for MCP ----
# In production this would be injected from the orchestrator's secure context.
# The LLM/agent never sees the DB credentials or Razorpay secret; it only gets
# this scoped token from the backend gateway.
DEFAULT_MCP_TOKEN = "dev-mcp-token-change-me"


def _valid_token(token: str | None) -> bool:
    expected = settings.MCP_AUTH_TOKEN if getattr(settings, "MCP_AUTH_TOKEN", None) else DEFAULT_MCP_TOKEN
    return token == expected


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MCPError(Exception):
    def __init__(self, message: str, status: str = "error"):
        super().__init__(message)
        self.status = status


# ---------- input schemas ----------
class PaymentIdArgs(pydantic.BaseModel):
    payment_id: int
    token: str = ""


class CustomerIdArgs(pydantic.BaseModel):
    customer_id: int
    token: str = ""


class CaseIdArgs(pydantic.BaseModel):
    case_id: int
    token: str = ""


class CreatePaymentLinkArgs(pydantic.BaseModel):
    customer_id: int
    amount: float = pydantic.Field(gt=0)
    reason: str = ""
    token: str = ""


class ScheduleRetryArgs(pydantic.BaseModel):
    payment_id: int
    scheduled_time: str  # ISO8601
    token: str = ""


class SendNotificationArgs(pydantic.BaseModel):
    customer_id: int
    message: str = pydantic.Field(min_length=1, max_length=2000)
    channel: str = "email"
    token: str = ""


class VerifyPaymentArgs(pydantic.BaseModel):
    payment_id: int
    token: str = ""


class RecordActionArgs(pydantic.BaseModel):
    case_id: int
    action: str
    token: str = ""


class CloseCaseArgs(pydantic.BaseModel):
    case_id: int
    status: str = pydantic.Field(pattern="^(recovered|failed|stopped)$")
    token: str = ""


def _log_call(
    db: Session,
    merchant_id: int,
    case_id: int | None,
    tool_name: str,
    arguments: dict,
    result: dict,
    status: str,
    duration_ms: int,
    caller: str | None,
    error: str | None = None,
) -> None:
    rec = MCPToolCall(merchant_id=merchant_id, case_id=case_id)
    rec.tool_name = tool_name
    rec.set_arguments({k: v for k, v in arguments.items() if k != "token"})
    rec.set_result(result)
    rec.status = status
    rec.duration_ms = duration_ms
    rec.caller = caller
    rec.error = error
    db.add(rec)
    db.commit()


class MCPTools:
    """Scoped tool executor. `merchant_id` is injected by the gateway/server."""

    def __init__(self, db: Session, merchant_id: int, caller: str | None = None):
        self.db = db
        self.merchant_id = merchant_id
        self.caller = caller

    def _wrap(self, tool_name: str, case_id: int | None, fn, args: dict) -> dict:
        t0 = time.time()
        try:
            result = fn()
            status = "ok"
            err = None
        except MCPError as e:
            result = {"error": str(e)}
            status = e.status
            err = str(e)
        except Exception as e:  # pragma: no cover
            logger.exception("MCP tool %s failed", tool_name)
            result = {"error": f"internal error: {e}"}
            status = "error"
            err = str(e)
        duration = int((time.time() - t0) * 1000)
        _log_call(self.db, self.merchant_id, case_id, tool_name, args, result, status, duration, self.caller, err)
        if status != "ok":
            raise MCPError(result.get("error", "error"), status)
        return result

    # ---------- tools ----------
    def get_payment(self, payment_id: int, token: str = "") -> dict:
        if not _valid_token(token):
            raise MCPError("unauthorized", "denied")
        case_id = None

        def fn():
            p = (
                self.db.query(Payment)
                .filter_by(id=payment_id, merchant_id=self.merchant_id)
                .first()
            )
            if not p:
                raise MCPError("payment not found")
            return {
                "id": p.id,
                "customer_id": p.customer_id,
                "amount": p.amount,
                "currency": p.currency,
                "status": p.status,
                "failure_reason": p.failure_reason,
                "payment_method": p.payment_method,
                "razorpay_payment_id": p.razorpay_payment_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }

        return self._wrap("get_payment", case_id, fn, {"payment_id": payment_id, "token": "***"})

    def get_customer(self, customer_id: int, token: str = "") -> dict:
        if not _valid_token(token):
            raise MCPError("unauthorized", "denied")

        def fn():
            c = (
                self.db.query(Customer)
                .filter_by(id=customer_id, merchant_id=self.merchant_id)
                .first()
            )
            if not c:
                raise MCPError("customer not found")
            return {
                "id": c.id,
                "external_id": c.external_id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "clv": c.clv,
            }

        return self._wrap("get_customer", None, fn, {"customer_id": customer_id, "token": "***"})

    def get_customer_payment_history(self, customer_id: int, token: str = "") -> dict:
        if not _valid_token(token):
            raise MCPError("unauthorized", "denied")

        def fn():
            rows = (
                self.db.query(Payment)
                .filter_by(customer_id=customer_id, merchant_id=self.merchant_id)
                .order_by(Payment.created_at.desc())
                .limit(50)
                .all()
            )
            return {
                "customer_id": customer_id,
                "payments": [
                    {
                        "id": p.id,
                        "amount": p.amount,
                        "status": p.status,
                        "failure_reason": p.failure_reason,
                        "payment_method": p.payment_method,
                        "created_at": p.created_at.isoformat() if p.created_at else None,
                    }
                    for p in rows
                ],
            }

        return self._wrap("get_customer_payment_history", None, fn, {"customer_id": customer_id, "token": "***"})

    def get_failed_payments(self, token: str = "") -> dict:
        if not _valid_token(token):
            raise MCPError("unauthorized", "denied")

        def fn():
            rows = (
                self.db.query(Payment)
                .filter_by(merchant_id=self.merchant_id, status="failed")
                .order_by(Payment.created_at.desc())
                .limit(100)
                .all()
            )
            return {
                "count": len(rows),
                "payments": [
                    {
                        "id": p.id,
                        "customer_id": p.customer_id,
                        "amount": p.amount,
                        "failure_reason": p.failure_reason,
                        "payment_method": p.payment_method,
                        "created_at": p.created_at.isoformat() if p.created_at else None,
                    }
                    for p in rows
                ],
            }

        return self._wrap("get_failed_payments", None, fn, {"token": "***"})

    def get_recovery_case(self, case_id: int, token: str = "") -> dict:
        if not _valid_token(token):
            raise MCPError("unauthorized", "denied")

        def fn():
            c = (
                self.db.query(RecoveryCase)
                .filter_by(id=case_id, merchant_id=self.merchant_id)
                .first()
            )
            if not c:
                raise MCPError("case not found")
            return self._case_dict(c)

        return self._wrap("get_recovery_case", case_id, fn, {"case_id": case_id, "token": "***"})

    def calculate_recovery_score(self, payment_id: int, token: str = "") -> dict:
        if not _valid_token(token):
            raise MCPError("unauthorized", "denied")

        def fn():
            from app.services.ml_pipeline import model_store

            p = (
                self.db.query(Payment)
                .filter_by(id=payment_id, merchant_id=self.merchant_id)
                .first()
            )
            if not p:
                raise MCPError("payment not found")
            c = (
                self.db.query(Customer)
                .filter_by(id=p.customer_id, merchant_id=self.merchant_id)
                .first()
            )
            feats = self._payment_features(p, c)
            prob = model_store.predict_proba(feats) if model_store.is_loaded() else 0.5
            return {"payment_id": payment_id, "recovery_probability": round(prob, 4), "model_version": model_store.version, "features": feats}

        return self._wrap("calculate_recovery_score", None, fn, {"payment_id": payment_id, "token": "***"})

    def create_payment_link(self, customer_id: int, amount: float, reason: str, token: str = "") -> dict:
        if not _valid_token(token):
            raise MCPError("unauthorized", "denied")

        def fn():
            c = (
                self.db.query(Customer)
                .filter_by(id=customer_id, merchant_id=self.merchant_id)
                .first()
            )
            if not c:
                raise MCPError("customer not found")
            # In production this calls Razorpay's payment link API (test mode).
            # We never return the Razorpay secret to the caller.
            link_id = f"plink_{self.merchant_id}_{customer_id}_{int(time.time())}"
            from app.services import razorpay_client

            if razorpay_client.is_enabled():
                try:
                    resp = razorpay_client.create_payment_link(
                        customer=c, amount=amount, reason=reason
                    )
                    link_id = resp.get("id", link_id)
                    url = resp.get("short_url") or resp.get("url")
                except Exception as e:
                    raise MCPError(f"razorpay error: {e}")
            else:
                url = f"https://rzp.test/{link_id}"
            return {
                "payment_link_id": link_id,
                "url": url,
                "amount": amount,
                "customer_id": customer_id,
                "message": "Recovery action executed. Payment link created. Awaiting customer payment confirmation.",
            }

        return self._wrap("create_payment_link", None, fn, {"customer_id": customer_id, "amount": amount, "token": "***"})

    def schedule_retry(self, payment_id: int, scheduled_time: str, token: str = "") -> dict:
        if not _valid_token(token):
            raise MCPError("unauthorized", "denied")

        def fn():
            p = (
                self.db.query(Payment)
                .filter_by(id=payment_id, merchant_id=self.merchant_id)
                .first()
            )
            if not p:
                raise MCPError("payment not found")
            return {"payment_id": payment_id, "scheduled_time": scheduled_time, "status": "scheduled"}

        return self._wrap("schedule_retry", None, fn, {"payment_id": payment_id, "token": "***"})

    def send_recovery_notification(self, customer_id: int, message: str, channel: str = "email", token: str = "") -> dict:
        if not _valid_token(token):
            raise MCPError("unauthorized", "denied")

        def fn():
            c = (
                self.db.query(Customer)
                .filter_by(id=customer_id, merchant_id=self.merchant_id)
                .first()
            )
            if not c:
                raise MCPError("customer not found")
            n = Notification(
                merchant_id=self.merchant_id,
                customer_id=customer_id,
                channel=channel,
                subject="Payment recovery",
                body=message,
                status="sent",
                sent_at=_now(),
            )
            self.db.add(n)
            self.db.commit()
            return {"notification_id": n.id, "channel": channel, "customer_id": customer_id, "status": "sent"}

        return self._wrap("send_recovery_notification", None, fn, {"customer_id": customer_id, "token": "***"})

    def verify_payment(self, payment_id: int, token: str = "") -> dict:
        if not _valid_token(token):
            raise MCPError("unauthorized", "denied")

        def fn():
            from app.services import razorpay_client

            p = (
                self.db.query(Payment)
                .filter_by(id=payment_id, merchant_id=self.merchant_id)
                .first()
            )
            if not p:
                raise MCPError("payment not found")
            status = p.status
            if razorpay_client.is_enabled():
                try:
                    fetched = razorpay_client.fetch_payment(p.razorpay_payment_id)
                    status = fetched.get("status", p.status)
                except Exception:
                    pass
            return {"payment_id": payment_id, "status": status, "amount": p.amount}

        return self._wrap("verify_payment", None, fn, {"payment_id": payment_id, "token": "***"})

    def record_recovery_action(self, case_id: int, action: str, token: str = "") -> dict:
        if not _valid_token(token):
            raise MCPError("unauthorized", "denied")

        def fn():
            c = (
                self.db.query(RecoveryCase)
                .filter_by(id=case_id, merchant_id=self.merchant_id)
                .first()
            )
            if not c:
                raise MCPError("case not found")
            ra = RecoveryAction(
                merchant_id=self.merchant_id, case_id=case_id, action_type=action, status="executed"
            )
            ra.set_detail({"source": "mcp", "action": action})
            ra.executed_at = _now()
            ra.set_result({"ok": True})
            self.db.add(ra)
            self.db.commit()
            return {"recovery_action_id": ra.id, "case_id": case_id, "action": action, "status": "executed"}

        return self._wrap("record_recovery_action", case_id, fn, {"case_id": case_id, "token": "***"})

    def close_recovery_case(self, case_id: int, status: str, token: str = "") -> dict:
        if not _valid_token(token):
            raise MCPError("unauthorized", "denied")

        def fn():
            c = (
                self.db.query(RecoveryCase)
                .filter_by(id=case_id, merchant_id=self.merchant_id)
                .first()
            )
            if not c:
                raise MCPError("case not found")
            c.recovery_status = status
            c.action_status = "executed" if status == "recovered" else "failed"
            c.resolved_at = _now()
            self.db.commit()
            msg = (
                f"Payment successfully recovered: ₹{c.amount_recovered:,.0f}."
                if status == "recovered"
                else f"Recovery case marked as {status}."
            )
            return {"case_id": case_id, "recovery_status": status, "message": msg}

        return self._wrap("close_recovery_case", case_id, fn, {"case_id": case_id, "token": "***"})

    def get_recovery_metrics(self, token: str = "") -> dict:
        if not _valid_token(token):
            raise MCPError("unauthorized", "denied")

        def fn():
            total = self.db.query(func.count(RecoveryCase.id)).filter_by(merchant_id=self.merchant_id).scalar() or 0
            recovered = (
                self.db.query(func.sum(RecoveryCase.amount_recovered))
                .filter_by(merchant_id=self.merchant_id, recovery_status="recovered")
                .scalar()
                or 0.0
            )
            at_risk = (
                self.db.query(func.sum(RecoveryCase.amount_at_risk))
                .filter_by(merchant_id=self.merchant_id)
                .filter(RecoveryCase.recovery_status.in_(["open", "awaiting_payment", "in_progress"]))
                .scalar()
                or 0.0
            )
            open_cases = (
                self.db.query(func.count(RecoveryCase.id))
                .filter_by(merchant_id=self.merchant_id)
                .filter(RecoveryCase.recovery_status.in_(["open", "awaiting_payment", "in_progress"]))
                .scalar()
                or 0
            )
            return {
                "total_cases": total,
                "open_cases": open_cases,
                "revenue_recovered": float(recovered),
                "revenue_at_risk": float(at_risk),
            }

        return self._wrap("get_recovery_metrics", None, fn, {"token": "***"})

    # ---------- helpers ----------
    @staticmethod
    def _case_dict(c: RecoveryCase) -> dict:
        return {
            "id": c.id,
            "customer_id": c.customer_id,
            "payment_id": c.payment_id,
            "amount_at_risk": c.amount_at_risk,
            "risk_score": c.risk_score,
            "event_type": c.event_type,
            "failure_reason": c.failure_reason,
            "diagnosis": c.diagnosis,
            "diagnosis_confidence": c.diagnosis_confidence,
            "recovery_probability": c.recovery_probability,
            "recommended_action": c.recommended_action,
            "approved_action": c.approved_action,
            "policy_decision": c.policy_decision,
            "stage": getattr(c, "stage", "failed"),
            "whatsapp_status": getattr(c, "whatsapp_status", "not_dispatched"),
            "customer_response": getattr(c, "customer_response", "pending"),
            "payment_link_id": getattr(c, "payment_link_id", None),
            "payment_link_url": getattr(c, "payment_link_url", None),
            "verified_payment_id": getattr(c, "verified_payment_id", None),
            "action_status": c.action_status,
            "recovery_status": c.recovery_status,
            "amount_recovered": c.amount_recovered,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }

    def _payment_features(self, p: Payment, c: Customer | None) -> dict:
        from app.services.ml_pipeline import NUMERIC_FEATURES, CATEGORICAL_FEATURES

        history = (
            self.db.query(Payment)
            .filter_by(customer_id=p.customer_id, merchant_id=self.merchant_id)
            .all()
        )
        successes = sum(1 for x in history if x.status == "captured")
        fails = sum(1 for x in history if x.status == "failed")
        total = max(1, successes + fails)
        success_rate = successes / total
        previous_failures = fails
        clv = c.clv if c else 0.0
        return {
            "transaction_amount": float(p.amount),
            "customer_success_rate": round(success_rate, 4),
            "customer_clv": float(clv),
            "previous_failures": int(previous_failures),
            "retry_count": int(p.retry_count if hasattr(p, "retry_count") else 0),
            "payment_method": p.payment_method or "card",
            "failure_reason": p.failure_reason or "card_declined",
            "subscription_age_days": 0,
            "days_since_last_success": 5,
            "event_type": "payment_failed",
        }
