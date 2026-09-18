"""Detection Agent.

Finds revenue at risk from failed payments, checkout abandonment, subscription
failures and overdue receivables, computes a risk score, and opens a recovery
case. Output recorded as RecoveryCase + AgentDecision.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agents.base import AgentContext, BaseAgent
from app.models.payments import Order, Payment, Subscription
from app.models.recovery import RecoveryCase


# Recoverability weight per failure reason (higher => lower risk).
_REASON_RISK = {
    "insufficient_funds": 0.4,
    "network_error": 0.35,
    "timeout": 0.35,
    "card_declined": 0.6,
    "incorrect_cvv": 0.5,
    "expired_card": 0.7,
    "payment_cancelled": 0.85,
    "fraud_blocked": 0.95,
    "subscription_hard_fail": 0.8,
    "authentication_failed": 0.55,
}


class DetectionAgent(BaseAgent):
    name = "detection"

    def _risk_score(self, amount: float, failure_reason: str | None, customer_history: dict) -> float:
        base = _REASON_RISK.get(failure_reason or "card_declined", 0.6)
        # Larger amounts are riskier to recover automatically.
        amount_factor = min(amount / 100000.0, 1.0) * 0.15
        # More prior failures increase risk of non-recovery.
        prev_fail = customer_history.get("previous_failures", 0)
        prev_factor = min(prev_fail * 0.05, 0.2)
        score = base + amount_factor + prev_factor
        return round(min(max(score, 0.05), 0.99), 3)

    def detect_failed_payment(self, payment: Payment, reason: str | None = None) -> RecoveryCase:
        run = self.ctx.start_run(self.name, case_id=None)
        reason = reason or payment.failure_reason
        hist = self._customer_history(payment.customer_id)
        risk = self._risk_score(payment.amount, reason, hist)
        note = (
            f"Failed payment {payment.id} of {payment.amount} {payment.currency} "
            f"due to '{reason}'. Customer has {hist['previous_failures']} prior failures."
        )
        case = RecoveryCase(
            merchant_id=self.ctx.merchant_id,
            customer_id=payment.customer_id,
            payment_id=payment.id,
            amount_at_risk=float(payment.amount),
            risk_score=risk,
            event_type="payment_failed",
            failure_reason=reason,
            detection_reason=note,
            recovery_status="open",
            action_status="pending",
        )
        self.ctx.db.add(case)
        self.ctx.db.commit()
        self.ctx.db.refresh(case)
        run.case_id = case.id
        self.ctx.record_decision(
            run, "detect", {"payment_id": payment.id, "failure_reason": reason},
            {"case_id": case.id, "amount_at_risk": case.amount_at_risk, "risk_score": risk, "event_type": case.event_type},
            confidence=risk,
        )
        self.ctx.finish_run(run)
        return case

    def detect_abandoned_order(self, order: Order) -> RecoveryCase:
        run = self.ctx.start_run(self.name)
        hist = self._customer_history(order.customer_id)
        risk = self._risk_score(order.amount, "payment_cancelled", hist)
        note = f"Checkout abandonment on order {order.id} ({order.amount} {order.currency})."
        case = RecoveryCase(
            merchant_id=self.ctx.merchant_id,
            customer_id=order.customer_id,
            order_id=order.id,
            amount_at_risk=float(order.amount),
            risk_score=risk,
            event_type="checkout_abandoned",
            failure_reason="payment_cancelled",
            detection_reason=note,
            recovery_status="open",
            action_status="pending",
        )
        self.ctx.db.add(case)
        self.ctx.db.commit()
        self.ctx.db.refresh(case)
        run.case_id = case.id
        self.ctx.record_decision(run, "detect", {"order_id": order.id}, {"case_id": case.id, "risk_score": risk}, confidence=risk)
        self.ctx.finish_run(run)
        return case

    def detect_subscription_failure(self, sub: Subscription) -> RecoveryCase:
        run = self.ctx.start_run(self.name)
        hist = self._customer_history(sub.customer_id)
        risk = self._risk_score(sub.amount, "subscription_hard_fail", hist)
        note = f"Subscription {sub.id} payment failed (failures={sub.failure_count})."
        case = RecoveryCase(
            merchant_id=self.ctx.merchant_id,
            customer_id=sub.customer_id,
            subscription_id=sub.id,
            amount_at_risk=float(sub.amount),
            risk_score=risk,
            event_type="subscription_failed",
            failure_reason="subscription_hard_fail",
            detection_reason=note,
            recovery_status="open",
            action_status="pending",
        )
        self.ctx.db.add(case)
        self.ctx.db.commit()
        self.ctx.db.refresh(case)
        run.case_id = case.id
        self.ctx.record_decision(run, "detect", {"subscription_id": sub.id}, {"case_id": case.id, "risk_score": risk}, confidence=risk)
        self.ctx.finish_run(run)
        return case

    def _customer_history(self, customer_id: int) -> dict:
        from app.models.payments import Payment as P

        rows = self.ctx.db.query(P).filter_by(customer_id=customer_id, merchant_id=self.ctx.merchant_id).all()
        fails = sum(1 for r in rows if r.status == "failed")
        successes = sum(1 for r in rows if r.status == "captured")
        return {"previous_failures": fails, "successes": successes, "total": len(rows)}
