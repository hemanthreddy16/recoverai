"""Recovery Agent.

Executes the POLICY-APPROVED action through controlled MCP tools only. It never
touches payments directly. On success it records the action and marks the case
executed; otherwise it marks failed and the Verification Agent handles cleanup.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agents.base import AgentContext, BaseAgent
from app.models.recovery import RecoveryCase


class RecoveryAgent(BaseAgent):
    name = "recovery"

    def execute(self, case: RecoveryCase) -> RecoveryCase:
        run = self.ctx.start_run(self.name, case_id=case.id)
        action = case.approved_action or case.recommended_action
        outcome = "executed"
        detail = {}

        try:
            if action == "stop_recovery":
                case.action_status = "executed"
                case.recovery_status = "stopped"
                case.resolved_at = datetime.now(timezone.utc)
                detail = {"note": "Recovery stopped per policy."}
            elif action == "escalate_to_human":
                # No financial operation; flag for human.
                case.action_status = "pending"
                detail = {"note": "Escalated to human queue."}
            elif action == "retry_later":
                if case.payment_id:
                    when = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
                    r = self.ctx.gateway.schedule_retry(case.payment_id, when)
                    detail = r
                else:
                    r = self.ctx.gateway.send_recovery_notification(
                        case.customer_id, "Please retry your payment.", "email"
                    )
                    detail = r
                case.action_status = "executed"
                case.retry_count = (case.retry_count or 0) + 1
            elif action == "create_payment_link":
                r = self.ctx.gateway.create_payment_link(
                    case.customer_id, float(case.amount_at_risk), case.failure_reason or "recovery"
                )
                detail = r
                case.action_status = "executed"
            elif action in ("send_recovery_notification", "subscription_recovery"):
                msg = self._message(case)
                r = self.ctx.gateway.send_recovery_notification(case.customer_id, msg, "email")
                detail = r
                case.action_status = "executed"
            else:
                detail = {"note": f"No-op for action {action}"}
                case.action_status = "executed"

            if case.action_status == "executed" and action not in ("escalate_to_human", "stop_recovery"):
                self.ctx.gateway.record_recovery_action(case.id, action)

        except Exception as e:
            outcome = "failed"
            detail = {"error": str(e)}
            case.action_status = "failed"

        self.ctx.db.commit()
        self.ctx.record_decision(
            run, "recover",
            {"approved_action": action, "policy_decision": case.policy_decision},
            {"outcome": outcome, "detail": detail},
            confidence=0.9 if outcome == "executed" else 0.2,
        )
        self.ctx.finish_run(run, status="success" if outcome != "failed" else "error",
                            error=None if outcome != "failed" else str(detail))
        return case

    @staticmethod
    def _message(case: RecoveryCase) -> str:
        return (
            f"Hi, we noticed an issue with your payment of "
            f"{case.amount_at_risk} ({case.event_type}). You can complete it securely here: "
            f"[recovery link]. Reference case #{case.id}."
        )
