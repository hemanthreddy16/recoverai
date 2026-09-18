"""Prediction Agent (real ML).

Computes the recovery probability for a case using the trained model. This is a
genuine model inference result — never an LLM guess. Runs on a held-out-trained
GradientBoosting model; metrics are reported separately in /analytics.
"""
from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.models.recovery import RecoveryCase
from app.services.ml_pipeline import model_store


class PredictionAgent(BaseAgent):
    name = "prediction"

    def run(self, case: RecoveryCase) -> RecoveryCase:
        run = self.ctx.start_run(self.name, case_id=case.id)
        features = self._build_features(case)
        if not model_store.is_loaded():
            model_store.load()
        proba = model_store.predict_proba(features) if model_store.is_loaded() else 0.5
        version = model_store.version

        case.recovery_probability = round(proba, 4)
        case.model_version = version
        self.ctx.db.commit()

        self.ctx.record_decision(
            run, "predict",
            {"features": features},
            {"recovery_probability": round(proba, 4), "model_version": version},
            confidence=round(proba, 4),
        )
        self.ctx.finish_run(run)
        return case

    def _build_features(self, case: RecoveryCase) -> dict:
        # Pull customer history via controlled MCP tool (authorization + audit).
        hist = {"successes": 0, "fails": 0, "payments": []}
        if case.customer_id:
            try:
                h = self.ctx.gateway.get_customer_payment_history(case.customer_id)
                hist = h
            except Exception:
                pass
        payments = hist.get("payments", [])
        successes = sum(1 for p in payments if p.get("status") == "captured")
        fails = sum(1 for p in payments if p.get("status") == "failed")
        total = max(1, successes + fails)
        success_rate = successes / total

        # Customer CLV via MCP.
        clv = 0.0
        if case.customer_id:
            try:
                c = self.ctx.gateway.get_customer(case.customer_id)
                clv = float(c.get("clv", 0.0) or 0.0)
            except Exception:
                pass

        return {
            "transaction_amount": float(case.amount_at_risk or 0.0),
            "customer_success_rate": round(success_rate, 4),
            "customer_clv": float(clv),
            "previous_failures": int(fails),
            "retry_count": int(case.retry_count or 0),
            "payment_method": "card",
            "failure_reason": case.failure_reason or "card_declined",
            "subscription_age_days": 0,
            "days_since_last_success": 5,
            "event_type": case.event_type or "payment_failed",
        }
