"""Policy Engine (mandatory guardrail).

The LLM/agents NEVER have unrestricted authority over financial operations.
Every recommended action must pass through this engine, which decides:
  - "auto"      -> safe to execute without a human
  - "approval"  -> requires human approval (HIGH/MEDIUM risk or disabled auto)
  - "denied"    -> not permitted under current policy

Risk tiers follow the spec: LOW (reminder/notification) automatic, MEDIUM
(payment link / retry) configurable approval, HIGH (large amount / repeated
failures / fraud) human approval.
"""
from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.models.recovery import MerchantPolicy, RecoveryCase


class PolicyEngine(BaseAgent):
    name = "policy"

    def evaluate(self, case: RecoveryCase, policy: MerchantPolicy) -> RecoveryCase:
        run = self.ctx.start_run(self.name, case_id=case.id)
        prob = case.recovery_probability or 0.0
        amount = case.amount_at_risk or 0.0
        action = case.recommended_action or "send_recovery_notification"

        tier = self._risk_tier(case, policy)
        decision, approved, reason = self._decide(action, tier, policy, case)

        case.policy_decision = decision
        case.approved_action = approved if decision != "denied" else None
        case.policy_reason = reason
        self.ctx.db.commit()

        self.ctx.record_decision(
            run, "policy",
            {"tier": tier, "recommended_action": action, "prob": prob, "amount": amount},
            {"policy_decision": decision, "approved_action": case.approved_action, "reason": reason},
            confidence=0.99,
        )
        self.ctx.finish_run(run)
        return case

    def _risk_tier(self, case: RecoveryCase, policy: MerchantPolicy) -> str:
        amount = case.amount_at_risk or 0.0
        prob = case.recovery_probability or 0.0
        if (
            amount >= policy.high_value_threshold
            or case.failure_reason == "fraud_blocked"
            or case.retry_count > policy.retry_limit
        ):
            return "HIGH"
        if prob >= policy.automatic_threshold and amount < policy.high_value_threshold and case.retry_count <= policy.retry_limit:
            return "LOW"
        return "MEDIUM"

    def _decide(self, action, tier, policy, case):
        if action == "stop_recovery":
            return "auto", "stop_recovery", "Low-value/low-probability case; stopping recovery automatically is safe."
        if action == "escalate_to_human":
            return "approval", "escalate_to_human", "Strategy recommends human escalation; human approval required."
        if tier == "HIGH":
            return "approval", action, "HIGH risk (large amount / repeat failures / fraud) requires human approval."
        if tier == "LOW":
            permitted = self._auto_permitted(action, policy)
            if permitted:
                return "auto", action, f"LOW risk and action '{action}' is permitted for automatic execution."
            return "approval", action, f"LOW risk but '{action}' is disabled for auto; needs approval."
        # MEDIUM
        return "approval", action, "MEDIUM risk requires configurable human approval."

    @staticmethod
    def _auto_permitted(action: str, policy: MerchantPolicy) -> bool:
        if action == "retry_later":
            return policy.allow_auto_retry
        if action == "create_payment_link":
            return policy.allow_auto_payment_link
        if action in ("send_recovery_notification", "subscription_recovery"):
            return policy.allow_auto_notification
        return False
