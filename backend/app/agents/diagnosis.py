"""Diagnosis Agent.

Analyzes payment history, failure reason and customer behaviour to explain WHY
revenue was lost and recommends a recovery category. The numeric recovery
probability always comes from the ML model, never from this agent's text.
"""
from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.models.recovery import RecoveryCase

# Mapping of failure reason -> likely root cause + suggested recovery category.
CAUSE_MAP = {
    "insufficient_funds": ("Customer had insufficient balance at attempt time", "create_payment_link"),
    "network_error": ("Transient network error at gateway", "retry_later"),
    "timeout": ("Request timed out before completion", "retry_later"),
    "card_declined": ("Issuer declined the card", "send_recovery_notification"),
    "incorrect_cvv": ("CVV/OTP mismatch; recoverable with correction", "create_payment_link"),
    "expired_card": ("Card expired; customer action required", "send_recovery_notification"),
    "payment_cancelled": ("Customer abandoned before completing", "send_recovery_notification"),
    "fraud_blocked": ("Blocked by risk engine; unlikely automatic recovery", "escalate_to_human"),
    "subscription_hard_fail": ("Recurring charge failed; possible churn", "subscription_recovery"),
    "authentication_failed": ("3DS / authentication step failed", "create_payment_link"),
}
EVENT_CATEGORY = {
    "checkout_abandoned": "send_recovery_notification",
    "subscription_failed": "subscription_recovery",
    "overdue_receivable": "create_payment_link",
}


class DiagnosisAgent(BaseAgent):
    name = "diagnosis"

    def run(self, case: RecoveryCase) -> RecoveryCase:
        run = self.ctx.start_run(self.name, case_id=case.id)
        reason = case.failure_reason or "card_declined"

        history = {}
        if case.customer_id:
            hist = self.ctx.gateway.get_customer_payment_history(case.customer_id)
            history = {"payments": hist.get("payments", [])}
        successes = sum(1 for p in history.get("payments", []) if p.get("status") == "captured")
        fails = sum(1 for p in history.get("payments", []) if p.get("status") == "failed")

        cause, category = CAUSE_MAP.get(reason, ("Unclassified failure", "send_recovery_notification"))
        if case.event_type in EVENT_CATEGORY:
            category = EVENT_CATEGORY[case.event_type]

        factors = [cause]
        if fails >= 3:
            factors.append("Repeated prior failures indicate structural issue")
        if case.amount_at_risk and case.amount_at_risk > 50000:
            factors.append("High value increases need for human touch")
        if successes == 0 and (successes + fails) > 0:
            factors.append("No prior successful payments from this customer")

        confidence = 0.85 if reason in CAUSE_MAP else 0.5

        # Optional natural-language explanation (LLM or heuristic).
        explanation = self._explain(case, cause, factors)
        case.diagnosis = explanation
        case.diagnosis_confidence = confidence
        case.set_contributing_factors(factors)
        case.recommended_recovery_category = category
        self.ctx.db.commit()

        self.ctx.record_decision(
            run, "diagnose",
            {"failure_reason": reason, "history": {"successes": successes, "fails": fails}},
            {"diagnosis": explanation, "recommended_recovery_category": category, "confidence": confidence, "factors": factors},
            confidence=confidence,
        )
        self.ctx.finish_run(run)
        return case

    def _explain(self, case: RecoveryCase, cause: str, factors: list[str]) -> str:
        system = (
            "You are a payments analyst. Explain concisely (<=2 sentences) why a "
            "payment failed and what recovery category fits. Be factual."
        )
        user = (
            f"Event: {case.event_type}. Failure reason: {case.failure_reason}. "
            f"Amount at risk: {case.amount_at_risk}. Factors: {factors}."
        )
        text = self._ask_llm(system, user, max_tokens=200)
        if text:
            return text.strip()
        return f"{cause}. Recommended category: {case.recommended_recovery_category}."
