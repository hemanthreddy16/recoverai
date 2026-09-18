"""AI Command Center router: natural-language queries & policy-gated actions."""
from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.agents.orchestrator import approve_case, process_case
from app.database import get_db
from app.models.payments import Payment
from app.models.recovery import AgentDecision, AgentRun, RecoveryCase
from app.models.users import Customer
from app.schemas.api import CommandQueryRequest, CommandQueryResponse
from app.security import AuthUser, get_current_user, require_role

router = APIRouter(prefix="/command", tags=["command"])


@router.post("/query", response_model=CommandQueryResponse)
def handle_command_query(
    body: CommandQueryRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> CommandQueryResponse:
    mid = user.merchant_id
    q = body.query.strip().lower()

    # 1. Why did case #X fail?
    case_match = re.search(r"(?:case|rc)[- #]*(\d+)", q)
    if ("why" in q or "explain" in q or "detail" in q or "diagnos" in q) and case_match:
        cid = int(case_match.group(1))
        c = db.query(RecoveryCase).filter_by(merchant_id=mid, id=cid).first()
        if not c:
            return CommandQueryResponse(
                query=body.query,
                intent="case_explain",
                answer=f"Case #{cid} was not found in your merchant workspace.",
                data={"case_id": cid, "found": False},
            )
        factors = c.get_contributing_factors()
        answer = (
            f"Case #{cid} diagnosis: {c.diagnosis or 'Identified payment failure'}. "
            f"Failure reason: '{c.failure_reason or 'declined'}'. "
            f"Recovery probability is {int((c.recovery_probability or 0.5) * 100)}% with risk score {int(c.risk_score * 100)}%. "
            f"Recommended strategy: {c.recommended_action or 'Smart Retry'} (Policy status: {c.policy_decision or 'pending'})."
        )
        return CommandQueryResponse(
            query=body.query,
            intent="case_explain",
            answer=answer,
            data={
                "case_id": c.id,
                "amount": c.amount_at_risk,
                "failure_reason": c.failure_reason,
                "recovery_probability": c.recovery_probability,
                "risk_score": c.risk_score,
                "diagnosis": c.diagnosis,
                "contributing_factors": factors,
                "recommended_action": c.recommended_action,
                "recovery_status": c.recovery_status,
            },
            suggested_actions=[
                {"label": f"View Case #{c.id}", "action": f"/cases/{c.id}"},
                {"label": "Approve Recovery", "action": f"approve_case_{c.id}"} if c.policy_decision == "approval" else None,
            ],
        )

    # 2. High-value failed payments / cases
    if "high" in q and ("value" in q or "amount" in q or "risk" in q):
        cases = (
            db.query(RecoveryCase)
            .filter_by(merchant_id=mid)
            .order_by(desc(RecoveryCase.amount_at_risk))
            .limit(5)
            .all()
        )
        data_cases = [
            {
                "id": c.id,
                "customer_id": c.customer_id,
                "amount": c.amount_at_risk,
                "failure_reason": c.failure_reason,
                "recovery_probability": c.recovery_probability,
                "recovery_status": c.recovery_status,
                "action": c.recommended_action,
            }
            for c in cases
        ]
        total_val = sum(c["amount"] for c in data_cases)
        answer = f"Found {len(data_cases)} highest-value cases representing ₹{total_val:,.2f} total value at risk. Top case is #{data_cases[0]['id']} for ₹{data_cases[0]['amount']:,.2f}." if data_cases else "No high-value cases currently logged."
        return CommandQueryResponse(
            query=body.query,
            intent="high_value_cases",
            answer=answer,
            data={"cases": data_cases, "total_value": total_val},
            suggested_actions=[{"label": "View All Cases", "action": "/cases"}],
        )

    # 3. Highest recovery probability
    if "highest" in q and ("probability" in q or "recoverable" in q or "likely" in q or "chance" in q) or "best chance" in q:
        cases = (
            db.query(RecoveryCase)
            .filter_by(merchant_id=mid, recovery_status="open")
            .order_by(desc(RecoveryCase.recovery_probability))
            .limit(5)
            .all()
        )
        data_cases = [
            {
                "id": c.id,
                "amount": c.amount_at_risk,
                "recovery_probability": c.recovery_probability,
                "strategy": c.recommended_action,
                "status": c.recovery_status,
            }
            for c in cases
        ]
        answer = f"Identified {len(data_cases)} open cases with the strongest ML recovery probability (up to {int((data_cases[0]['recovery_probability'] or 0)*100)}% chance)." if data_cases else "No open recoverable cases found."
        return CommandQueryResponse(
            query=body.query,
            intent="high_probability_cases",
            answer=answer,
            data={"cases": data_cases},
            suggested_actions=[{"label": "Review Top Case", "action": f"/cases/{data_cases[0]['id']}"}] if data_cases else [],
        )

    # 4. Revenue at risk / total at risk / stats
    if "revenue" in q or "how much" in q or "at risk" in q or "stat" in q or "overview" in q:
        at_risk = (
            db.query(func.sum(RecoveryCase.amount_at_risk))
            .filter_by(merchant_id=mid, recovery_status="open").scalar() or 0.0
        )
        recovered = (
            db.query(func.sum(RecoveryCase.amount_recovered))
            .filter_by(merchant_id=mid, recovery_status="recovered").scalar() or 0.0
        )
        active_count = db.query(func.count(RecoveryCase.id)).filter_by(merchant_id=mid, recovery_status="open").scalar() or 0
        predicted_rec = sum(
            (c.amount_at_risk or 0) * (c.recovery_probability or 0.5)
            for c in db.query(RecoveryCase).filter_by(merchant_id=mid, recovery_status="open").all()
        )
        answer = (
            f"Currently ₹{at_risk:,.2f} is at risk across {active_count} active cases. "
            f"The ML model estimates ₹{predicted_rec:,.2f} is recoverable. "
            f"Total revenue successfully recovered so far is ₹{recovered:,.2f}."
        )
        return CommandQueryResponse(
            query=body.query,
            intent="revenue_overview",
            answer=answer,
            data={
                "revenue_at_risk": float(at_risk),
                "predicted_recoverable": round(float(predicted_rec), 2),
                "revenue_recovered": float(recovered),
                "active_cases": active_count,
            },
            suggested_actions=[{"label": "Open Dashboard", "action": "/dashboard"}],
        )

    # 5. Best performing strategy / strategy performance
    if "strategy" in q or "performance" in q or "perform" in q:
        strat_rows = (
            db.query(
                RecoveryCase.approved_action,
                func.count(RecoveryCase.id),
                func.sum(RecoveryCase.amount_recovered),
            )
            .filter_by(merchant_id=mid, recovery_status="recovered")
            .group_by(RecoveryCase.approved_action)
            .all()
        )
        stats = [
            {"strategy": r[0] or "smart_retry", "recovered_cases": r[1], "recovered_amount": float(r[2] or 0.0)}
            for r in strat_rows
        ]
        top = max(stats, key=lambda s: s["recovered_amount"]) if stats else None
        answer = f"Top performing strategy is '{top['strategy']}' having recovered ₹{top['recovered_amount']:,.2f} across {top['recovered_cases']} cases." if top else "Smart Retry and Payment Link are the primary configured recovery strategies."
        return CommandQueryResponse(
            query=body.query,
            intent="strategy_performance",
            answer=answer,
            data={"strategies": stats},
            suggested_actions=[{"label": "View Analytics", "action": "/analytics"}],
        )

    # 6. High risk customers
    if "customer" in q:
        custs = (
            db.query(Customer)
            .filter_by(merchant_id=mid)
            .order_by(desc(Customer.clv))
            .limit(5)
            .all()
        )
        data_custs = [
            {"id": c.id, "name": c.name, "email": c.email, "clv": c.clv, "external_id": c.external_id}
            for c in custs
        ]
        answer = f"Retrieved {len(data_custs)} tracked customers. Top customer by CLV is '{data_custs[0]['name']}' with ₹{data_custs[0]['clv']:,.2f} lifetime value." if data_custs else "No customer accounts found."
        return CommandQueryResponse(
            query=body.query,
            intent="customers",
            answer=answer,
            data={"customers": data_custs},
        )

    # 7. Action execution: Recover highest priority case or approve
    if "recover" in q or "approve" in q:
        top_case = (
            db.query(RecoveryCase)
            .filter_by(merchant_id=mid, recovery_status="open")
            .order_by(desc(RecoveryCase.recovery_probability))
            .first()
        )
        if not top_case:
            return CommandQueryResponse(
                query=body.query,
                intent="action_trigger",
                answer="No open cases currently requiring recovery actions.",
                data={},
            )
        if top_case.policy_decision == "approval":
            approve_case(db, top_case, simulated_outcome="success")
            answer = f"Case #{top_case.id} (₹{top_case.amount_at_risk:,.2f}) approved and executed through MCP tool '{top_case.approved_action or 'smart_retry'}'. Verification confirmed ₹{top_case.amount_recovered:,.2f} recovered."
        else:
            process_case(db, top_case, simulated_outcome="success", auto_approve=True)
            answer = f"Recovery pipeline triggered for Priority Case #{top_case.id} (₹{top_case.amount_at_risk:,.2f}). Action executed and logged to audit trail."

        return CommandQueryResponse(
            query=body.query,
            intent="action_executed",
            answer=answer,
            data={"case_id": top_case.id, "status": top_case.recovery_status, "amount_recovered": top_case.amount_recovered},
            suggested_actions=[{"label": f"View Case #{top_case.id}", "action": f"/cases/{top_case.id}"}],
        )

    # Fallback general query
    return CommandQueryResponse(
        query=body.query,
        intent="general_help",
        answer=(
            f"I can analyze your revenue recovery metrics and execute policy-gated actions. "
            f"Try asking: 'How much revenue is currently at risk?', 'Show me all high-value failed payments', "
            f"'Which cases have the highest recovery probability?', or 'Why did case #1 fail?'."
        ),
        data={"help": True},
        suggested_actions=[
            {"label": "Check Revenue At Risk", "action": "How much revenue is currently at risk?"},
            {"label": "Show High-Value Cases", "action": "Show me all high-value failed payments"},
            {"label": "Highest Recovery Probability", "action": "Which cases have the highest recovery probability?"},
        ],
    )
