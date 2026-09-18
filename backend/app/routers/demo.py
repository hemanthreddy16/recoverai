"""Demo Center router.

Lets a judge trigger realistic revenue-at-risk scenarios and watch the full
agent pipeline run live. Each scenario creates a real event, runs Detection ->
Diagnosis -> Prediction -> Strategy -> Policy -> Recovery -> Verification, and
returns the resulting case so the UI can render the timeline.

NO real money moves: recovery actions are executed through the MCP tool layer,
which either calls Razorpay Test Mode (if enabled) or a safe local simulation.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.detection import DetectionAgent
from app.agents.base import AgentContext
from app.agents.orchestrator import process_case
from app.database import get_db
from app.logging_setup import logger
from app.mcp.gateway import MCPGateway
from app.models.payments import Order, Payment, Subscription
from app.models.users import Customer
from app.models.recovery import RecoveryCase
from app.security import AuthUser, get_current_user
from app.services.llm import get_llm
from app.schemas.api import DemoResult, DemoScenarioRequest

router = APIRouter(prefix="/demo", tags=["demo"])

SCENARIOS = {
    "simple_payment_failure": {"reason": "card_declined", "amount": 2400, "outcome": "success", "kind": "payment"},
    "recoverable_payment_failure": {"reason": "insufficient_funds", "amount": 1800, "outcome": "success", "kind": "payment"},
    "repeated_payment_failure": {"reason": "card_declined", "amount": 1500, "outcome": "failure", "kind": "payment_repeat"},
    "high_value_payment": {"reason": "insufficient_funds", "amount": 90000, "outcome": "success", "kind": "payment"},
    "checkout_abandonment": {"reason": "payment_cancelled", "amount": 3200, "outcome": "success", "kind": "order"},
    "subscription_failure": {"reason": "subscription_hard_fail", "amount": 2200, "outcome": "failure", "kind": "subscription"},
    "failed_recovery": {"reason": "fraud_blocked", "amount": 12000, "outcome": "failure", "kind": "payment"},
    "successful_recovery": {"reason": "network_error", "amount": 5400, "outcome": "success", "kind": "payment"},
}


def _new_customer(db: Session, mid: int, clv: float = 5000.0) -> Customer:
    c = Customer(
        merchant_id=mid,
        external_id=f"DEMO-{random.randint(100000, 999999)}",
        name="Demo Customer",
        email="demo.customer@example.com",
        phone="9123456789",
        clv=clv,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("/scenarios")
def list_scenarios() -> dict:
    return {"scenarios": list(SCENARIOS.keys())}


@router.post("/run", response_model=DemoResult)
def run_scenario(body: DemoScenarioRequest, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)) -> DemoResult:
    spec = SCENARIOS.get(body.scenario)
    if not spec:
        raise HTTPException(status_code=400, detail=f"Unknown scenario. Choose from {list(SCENARIOS.keys())}")
    mid = user.merchant_id
    outcome = body.simulated_outcome or spec["outcome"]
    kind = spec["kind"]

    gateway = MCPGateway(db, mid, caller="demo")
    ctx = AgentContext(db, mid, get_llm(), gateway)

    # Build a realistic event.
    if kind == "order":
        c = _new_customer(db, mid)
        order = Order(merchant_id=mid, customer_id=c.id, amount=spec["amount"], status="abandoned", abandoned_at=datetime.now(timezone.utc))
        db.add(order)
        db.commit()
        db.refresh(order)
        case = DetectionAgent(ctx).detect_abandoned_order(order)
    elif kind == "subscription":
        c = _new_customer(db, mid)
        sub = Subscription(merchant_id=mid, customer_id=c.id, plan="pro", amount=spec["amount"], status="past_due", failure_count=1)
        db.add(sub)
        db.commit()
        db.refresh(sub)
        case = DetectionAgent(ctx).detect_subscription_failure(sub)
    else:  # payment
        c = _new_customer(db, mid, clv=random.uniform(2000, 40000))
        if kind == "payment_repeat":
            # Seed several prior failures for this customer.
            for _ in range(4):
                db.add(Payment(merchant_id=mid, customer_id=c.id, amount=spec["amount"], currency="INR", status="failed", failure_reason="card_declined"))
            db.commit()
        else:
            # Give the demo customer a positive payment history so recovery is
            # predicted likely and low-risk actions can run automatically.
            for _ in range(5):
                db.add(Payment(merchant_id=mid, customer_id=c.id, amount=random.uniform(500, 5000), currency="INR", status="captured"))
            db.commit()
        p = Payment(
            merchant_id=mid, customer_id=c.id, amount=spec["amount"], currency="INR",
            status="failed", failure_reason=spec["reason"], payment_method=random.choice(["card", "upi", "netbanking"]),
            created_at=datetime.now(timezone.utc),
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        case = DetectionAgent(ctx).detect_failed_payment(p, reason=spec["reason"])

    # High-value scenarios require human approval; in the demo we simulate approval.
    auto_approve = spec["amount"] >= 50000 or spec["reason"] == "fraud_blocked"
    case = process_case(db, case, simulated_outcome=outcome, auto_approve=auto_approve)
    logger.info("Demo scenario %s -> case %s (%s)", body.scenario, case.id, case.recovery_status)

    return DemoResult(
        case_id=case.id,
        event_type=case.event_type,
        amount_at_risk=case.amount_at_risk,
        recovery_probability=case.recovery_probability,
        recommended_action=case.recommended_action,
        policy_decision=case.policy_decision,
        approved_action=case.approved_action,
        recovery_status=case.recovery_status,
        amount_recovered=case.amount_recovered,
    )
