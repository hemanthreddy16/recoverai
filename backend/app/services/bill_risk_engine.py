"""AI Payment Risk Prediction Engine for Bills, EMIs, and Recurring Obligations.

Computes a calibrated 0-100 risk score, risk level (Low/Medium/High), and primary
explanatory reason based on customer transaction history, failure counts, days remaining,
amount magnitude, and category sensitivity.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.bills import BillEmi, BillRiskHistory
from app.models.payments import Payment
from app.models.recovery import RecoveryCase
from app.models.users import Customer


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RiskAssessmentResult:
    risk_score: int  # 0 to 100
    risk_level: str  # Low | Medium | High
    primary_reason: str
    contributing_factors: list[str]
    features_evaluated: dict[str, Any]


class BillRiskEngine:
    """Evaluates payment risk using an explainable multi-factor scoring model."""

    @staticmethod
    def classify_risk_level(score: int) -> str:
        """Classifies risk level based on required thresholds:
        - 0-30: Low
        - 31-70: Medium
        - 71-100: High
        """
        if score <= 30:
            return "Low"
        elif score <= 70:
            return "Medium"
        else:
            return "High"

    @classmethod
    def evaluate(
        cls,
        db: Session,
        bill: BillEmi,
        save_history: bool = True,
    ) -> RiskAssessmentResult:
        """Calculates AI risk score (0-100), risk level, and explanations."""
        now = _utcnow()
        due_d = bill.due_date.replace(tzinfo=timezone.utc) if bill.due_date.tzinfo is None else bill.due_date
        
        diff_days = (due_d.date() - now.date()).days
        days_remaining = max(0, diff_days)
        days_overdue = max(0, -diff_days)

        # Baseline score
        score = 15
        factors: list[str] = []
        primary_reason = "Standard upcoming obligation"

        # If already Paid, risk is minimal
        if bill.status == "Paid":
            score = 5
            primary_reason = "Obligation settled and marked as Paid"
            factors.append("Payment successfully captured and settled")
            level = "Low"
            res = RiskAssessmentResult(
                risk_score=score,
                risk_level=level,
                primary_reason=primary_reason,
                contributing_factors=factors,
                features_evaluated={"status": "Paid", "days_remaining": 0},
            )
            bill.risk_score = score
            bill.risk_level = level
            bill.risk_reason = primary_reason
            bill.set_risk_factors(factors)
            bill.last_evaluated_at = now
            return res

        # -------------------------------------------------------------
        # 1. Customer Payment History & Failure Analysis
        # -------------------------------------------------------------
        past_failed_count = 0
        past_success_count = 0
        past_late_count = 0
        customer_clv = 0.0

        if bill.customer_id:
            payments = db.query(Payment).filter_by(
                merchant_id=bill.merchant_id, customer_id=bill.customer_id
            ).all()
            past_failed_count = sum(1 for p in payments if p.status == "failed")
            past_success_count = sum(1 for p in payments if p.status in ["captured", "paid", "refunded"])

            # Check previous recovery cases
            past_cases = db.query(RecoveryCase).filter_by(
                merchant_id=bill.merchant_id, customer_id=bill.customer_id
            ).all()
            past_late_count = len(past_cases)

            cust = db.query(Customer).filter_by(id=bill.customer_id).first()
            if cust:
                customer_clv = cust.clv or 0.0

        # Customer failure penalties
        if past_failed_count >= 2:
            score += 35
            factors.append(f"Previous payment failed {past_failed_count} times")
            primary_reason = f"Previous payment failed {past_failed_count} times"
        elif past_failed_count == 1:
            score += 20
            factors.append("Customer had 1 recent failed payment attempt")
            primary_reason = "Customer has recent payment failure history"

        # Late payment habit
        if past_late_count >= 2:
            score += 25
            factors.append(f"Customer frequently pays after the due date ({past_late_count} past recovery cases)")
            if past_failed_count < 2:
                primary_reason = "Customer frequently pays after the due date"

        # Positive customer track record discount
        if past_success_count >= 5 and past_failed_count == 0:
            score -= 15
            factors.append("Customer has reliable payment track record (5+ successful transactions)")

        # -------------------------------------------------------------
        # 2. Timing Velocity & Due Date Proximity
        # -------------------------------------------------------------
        if days_overdue > 0 or bill.status == "Overdue":
            if days_overdue >= 7:
                score += 55
                factors.append(f"Critical overdue obligation ({days_overdue} days overdue)")
                primary_reason = f"Critical overdue obligation ({days_overdue} days past deadline)"
            elif days_overdue >= 3:
                score += 45
                factors.append(f"Payment is overdue by {days_overdue} days")
                primary_reason = f"Payment is overdue by {days_overdue} days"
            else:
                score += 35
                factors.append(f"Obligation is {max(1, days_overdue)} days overdue")
                primary_reason = f"Payment is {max(1, days_overdue)} days overdue"
        elif days_remaining == 0 or bill.status == "Due Today":
            score += 25
            factors.append("Due date is today")
            if past_failed_count == 0:
                primary_reason = "Due date is today"
        elif days_remaining == 1:
            score += 20
            factors.append("Due date is tomorrow")
            if past_failed_count == 0 and score < 50:
                primary_reason = "Due date is tomorrow"
        elif days_remaining <= 3:
            score += 15
            factors.append(f"Due date is within {days_remaining} days")
        elif days_remaining <= 7:
            score += 8
            factors.append("Due date is within 7 days")

        # -------------------------------------------------------------
        # 3. Amount Magnitude Exposure
        # -------------------------------------------------------------
        if bill.amount >= 75000:
            score += 25
            factors.append(f"Large payment amount (₹{bill.amount:,.0f})")
            if days_remaining <= 2 or days_overdue > 0:
                primary_reason = f"Large payment amount (₹{bill.amount:,.0f}) with urgent deadline"
        elif bill.amount >= 30000:
            score += 15
            factors.append(f"Significant obligation amount (₹{bill.amount:,.0f})")
        elif bill.amount >= 15000:
            score += 8
            factors.append("Moderate obligation amount")

        # -------------------------------------------------------------
        # 4. Category Risk Sensitivity
        # -------------------------------------------------------------
        cat_lower = (bill.category or "").lower()
        if cat_lower == "emi":
            score += 12
            factors.append("EMI loan obligation carries high default penalty")
        elif cat_lower == "rent":
            score += 8
            factors.append("Commercial lease / rent recurring commitment")
        elif cat_lower == "insurance":
            score += 8
            factors.append("Insurance premium lapse risk")

        # Clamp score to 0-100
        score = max(0, min(100, score))
        risk_level = cls.classify_risk_level(score)

        # Ensure a descriptive primary reason
        if not factors:
            factors.append("Normal recurring cycle with no adverse flags detected")

        # Save updates to bill model
        bill.risk_score = score
        bill.risk_level = risk_level
        bill.risk_reason = primary_reason
        bill.set_risk_factors(factors)
        bill.last_evaluated_at = now

        # Optionally record in BillRiskHistory
        if save_history:
            history = BillRiskHistory(
                bill_id=bill.id,
                merchant_id=bill.merchant_id,
                risk_score=score,
                risk_level=risk_level,
                risk_reason=primary_reason,
                evaluated_at=now,
            )
            history.set_factors(factors)
            db.add(history)
            db.commit()

        return RiskAssessmentResult(
            risk_score=score,
            risk_level=risk_level,
            primary_reason=primary_reason,
            contributing_factors=factors,
            features_evaluated={
                "amount": bill.amount,
                "days_remaining": days_remaining,
                "days_overdue": days_overdue,
                "category": bill.category,
                "past_failures": past_failed_count,
                "past_successes": past_success_count,
                "past_late_cases": past_late_count,
                "customer_clv": customer_clv,
            },
        )


def evaluate_bill(db: Session, bill: BillEmi, save_history: bool = True) -> RiskAssessmentResult:
    return BillRiskEngine.evaluate(db, bill, save_history=save_history)
