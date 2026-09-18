"""Strategy Agent.

Selects the SAFEST recovery action given the model probability, amount, attempt
count, customer history, failure reason and risk. It only proposes an action;
the Policy Engine decides whether it may run automatically.
"""
from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.models.recovery import RecoveryCase

ACTION_BY_CATEGORY = {
    "retry_later": "retry_later",
    "create_payment_link": "create_payment_link",
    "send_recovery_notification": "send_recovery_notification",
    "subscription_recovery": "subscription_recovery",
    "escalate_to_human": "escalate_to_human",
}


class StrategyAgent(BaseAgent):
    name = "strategy"

    def run(self, case: RecoveryCase, policy=None) -> RecoveryCase:
        run = self.ctx.start_run(self.name, case_id=case.id)
        prob = case.recovery_probability or 0.0
        category = case.recommended_recovery_category or "send_recovery_notification"
        approval_threshold = (policy.automatic_threshold - 0.3) if policy else 0.35

        # --- decision logic ---
        if prob < 0.15:
            action, rationale = "stop_recovery", (
                "Recovery probability is extremely low; automatic outreach is not "
                "cost-effective. Recommend stopping or human review."
            )
        elif prob < approval_threshold and category in ("escalate_to_human", "send_recovery_notification"):
            action, rationale = "escalate_to_human", (
                f"Low predicted recovery probability ({prob:.2f}). Escalate to a "
                "human rather than spending automated attempts."
            )
        elif case.retry_count >= (policy.retry_limit if policy else 2):
            action, rationale = "escalate_to_human", (
                f"Retry budget exhausted ({case.retry_count} attempts). Require "
                "human approval before further action."
            )
        else:
            action = ACTION_BY_CATEGORY.get(category, "send_recovery_notification")
            rationale = (
                f"Model probability {prob:.2f} and diagnosis category '{category}' "
                f"support '{action}'. Amount at risk {case.amount_at_risk}, risk "
                f"score {case.risk_score}."
            )

        case.recommended_action = action
        case.strategy_rationale = rationale
        self.ctx.db.commit()

        self.ctx.record_decision(
            run, "strategy",
            {"recovery_probability": prob, "category": category, "retry_count": case.retry_count},
            {"recommended_action": action, "rationale": rationale},
            confidence=prob,
        )
        self.ctx.finish_run(run)
        return case
