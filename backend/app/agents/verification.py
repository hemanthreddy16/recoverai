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

    def run(
        self,
        case: RecoveryCase,
        simulated_outcome: str | None = None,
        verified_payment_id: str | None = None,
        verified_amount: float | None = None,
    ) -> RecoveryCase:
        run = self.ctx.start_run(self.name, case_id=case.id)

        # Idempotency check: If already recovered with this payment ID, do not double-count or reprocess
        if case.recovery_status == "recovered" and case.amount_recovered > 0:
            if verified_payment_id and case.verified_payment_id == verified_payment_id:
                self.ctx.finish_run(run, status="success")
                return case

        success = self._determine_success(case, simulated_outcome)
        recovered = 0.0
        status = "failed"
        detail = {}

        if success:
            recovered = float(verified_amount if verified_amount is not None else (case.amount_at_risk or 0.0))
            status = "recovered"
            pay_ref = verified_payment_id or f"pay_ver_{case.id}_{int(datetime.now(timezone.utc).timestamp())}"
            case.verified_payment_id = pay_ref
            case.customer_response = "paid"
            case.stage = "recovered"
            case.recovery_status = "recovered"
            case.action_status = "executed"
            case.amount_recovered = recovered
            case.resolved_at = datetime.now(timezone.utc)

            # Reflect the capture in our own payment record (orchestration state).
            if case.payment_id:
                p = self.ctx.db.query(Payment).filter_by(id=case.payment_id, merchant_id=self.ctx.merchant_id).first()
                if p:
                    p.status = "captured"
                    p.captured_at = datetime.now(timezone.utc)
            detail = {"verified": True, "method": "simulated" if simulated_outcome else "razorpay", "payment_id": pay_ref}
        else:
            case.stage = "payment_failed"
            case.amount_recovered = 0.0
            if (case.retry_count or 0) >= (case.max_attempts or 3):
                status = "failed"
                case.recovery_status = "failed"
                case.stage = "failed"
                case.action_status = "failed"
                case.resolved_at = datetime.now(timezone.utc)
            else:
                status = "awaiting_payment"
                case.recovery_status = "awaiting_payment"
                case.action_status = "pending"
            detail = {"verified": False, "method": "simulated" if simulated_outcome else "razorpay"}

        self.ctx.db.commit()

        # Close or update the case via the controlled MCP tool (audit + authorization).
        if status in ("recovered", "failed"):
            try:
                self.ctx.gateway.close_recovery_case(case.id, status)
            except Exception as e:
                detail["close_error"] = str(e)

        self.ctx.record_decision(
            run, "verify",
            {"simulated_outcome": simulated_outcome, "verified_payment_id": verified_payment_id},
            {"success": success, "amount_recovered": case.amount_recovered, "recovery_status": case.recovery_status, "stage": case.stage, "detail": detail},
            confidence=0.98 if success else 0.4,
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
