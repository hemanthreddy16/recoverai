"""Verification Agent.

Confirms whether the recovery actually succeeded, calculates the amount recovered,
and closes the case. It consumes real payment status (Razorpay in test mode) and
falls back to an explicit simulated outcome for the offline demo. Failed
recoveries are handled gracefully (no silent success).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.agents.base import AgentContext, BaseAgent
from app.models.payments import Payment
from app.models.recovery import RecoveryCase


class VerificationAgent(BaseAgent):
    name = "verification"

    def run(self, case: RecoveryCase, simulated_outcome: str | None = None) -> RecoveryCase:
        run = self.ctx.start_run(self.name, case_id=case.id)

        success = self._determine_success(case, simulated_outcome)
        recovered = 0.0
        status = "failed"
        detail = {}

        if success:
            recovered = float(case.amount_at_risk or 0.0)
            status = "recovered"
            # Reflect the capture in our own payment record (orchestration state).
            if case.payment_id:
                p = self.ctx.db.query(Payment).filter_by(id=case.payment_id, merchant_id=self.ctx.merchant_id).first()
                if p:
                    p.status = "captured"
                    p.captured_at = datetime.now(timezone.utc)
            detail = {"verified": True, "method": "simulated" if simulated_outcome else "razorpay"}
        else:
            detail = {"verified": False, "method": "simulated" if simulated_outcome else "razorpay"}

        case.amount_recovered = recovered
        case.recovery_status = status
        case.action_status = "executed" if status == "recovered" else "failed"
        case.resolved_at = datetime.now(timezone.utc)
        self.ctx.db.commit()

        # Close the case via the controlled MCP tool (audit + authorization).
        try:
            self.ctx.gateway.close_recovery_case(case.id, status)
        except Exception as e:
            detail["close_error"] = str(e)

        self.ctx.record_decision(
            run, "verify",
            {"simulated_outcome": simulated_outcome},
            {"success": success, "amount_recovered": recovered, "recovery_status": status, "detail": detail},
            confidence=0.95 if success else 0.6,
        )
        self.ctx.finish_run(run)
        return case

    def _determine_success(self, case: RecoveryCase, simulated_outcome: str | None) -> bool:
        if simulated_outcome == "success":
            return True
        if simulated_outcome == "failure":
            return False
        if case.payment_id:
            try:
                r = self.ctx.gateway.verify_payment(case.payment_id)
                return r.get("status") == "captured"
            except Exception:
                return False
        return False
