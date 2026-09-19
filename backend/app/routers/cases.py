"""Cases router: list, detail (with full audit timeline), approval."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.recovery import (
    AgentDecision,
    AgentRun,
    AuditLog,
    MCPToolCall,
    Notification,
    RecoveryCase,
)
from app.security import AuthUser, get_current_user
from app.services.llm import get_llm
from app.mcp.gateway import MCPGateway
from app.agents.base import AgentContext
from app.agents.orchestrator import approve_case
from app.agents.verification import VerificationAgent

from app.schemas.api import ApproveRequest, CaseCreate, CaseDetail, CaseOut, SimulateCustomerPaymentRequest

router = APIRouter(prefix="/cases", tags=["cases"])


def _merchant(user: AuthUser) -> int:
    return user.merchant_id


@router.get("", response_model=list[CaseOut])
def list_cases(
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> list[RecoveryCase]:
    q = db.query(RecoveryCase).filter_by(merchant_id=user.merchant_id)
    if status:
        q = q.filter_by(recovery_status=status)
    return q.order_by(RecoveryCase.created_at.desc()).limit(limit).all()


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: int, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)) -> CaseDetail:
    case = db.query(RecoveryCase).filter_by(id=case_id, merchant_id=user.merchant_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    detail = CaseDetail.model_validate(case)
    detail.contributing_factors = case.get_contributing_factors()
    return detail


@router.post("/{case_id}/approve", response_model=CaseDetail)
def approve(
    case_id: int,
    body: ApproveRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> CaseDetail:
    case = db.query(RecoveryCase).filter_by(id=case_id, merchant_id=user.merchant_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.policy_decision != "approval":
        raise HTTPException(status_code=400, detail="Case is not awaiting approval")

    # Record Human-in-the-Loop Audit Log
    db.add(
        AuditLog(
            merchant_id=user.merchant_id,
            actor="operator",
            action="case.approved",
            entity_type="recovery_case",
            entity_id=case.id,
            detail=json.dumps({"action": case.recommended_action, "outcome": body.simulated_outcome}),
        )
    )
    db.commit()

    case = approve_case(db, case, simulated_outcome=body.simulated_outcome)
    detail = CaseDetail.model_validate(case)
    detail.contributing_factors = case.get_contributing_factors()
    return detail


@router.post("/{case_id}/simulate-customer-payment", response_model=CaseDetail)
def simulate_customer_payment(
    case_id: int,
    body: SimulateCustomerPaymentRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> CaseDetail:
    case = db.query(RecoveryCase).filter_by(id=case_id, merchant_id=user.merchant_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Record Customer Payment Event in Audit Log
    db.add(
        AuditLog(
            merchant_id=user.merchant_id,
            actor="customer",
            action="payment.attempted" if body.outcome == "success" else "payment.failed",
            entity_type="recovery_case",
            entity_id=case.id,
            detail=json.dumps({"outcome": body.outcome, "amount": body.amount or case.amount_at_risk, "method": body.payment_method}),
        )
    )
    db.commit()

    gateway = MCPGateway(db, user.merchant_id, caller="simulate_payment")
    ctx = AgentContext(db, user.merchant_id, get_llm(), gateway)
    case = VerificationAgent(ctx).run(
        case,
        simulated_outcome=body.outcome,
        verified_payment_id=body.razorpay_payment_id,
        verified_amount=body.amount,
    )

    detail = CaseDetail.model_validate(case)
    detail.contributing_factors = case.get_contributing_factors()
    return detail


@router.post("", response_model=CaseDetail, status_code=201)
def create_case(
    body: CaseCreate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> CaseDetail:
    case = RecoveryCase(
        merchant_id=user.merchant_id,
        customer_id=body.customer_id,
        payment_id=body.payment_id,
        amount_at_risk=body.amount_at_risk,
        event_type=body.event_type,
        failure_reason=body.failure_reason,
        recovery_status="open",
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # Log case creation audit
    db.add(
        AuditLog(
            merchant_id=user.merchant_id,
            actor="api",
            action="case.created",
            entity_type="recovery_case",
            entity_id=case.id,
            detail=json.dumps({"amount_at_risk": body.amount_at_risk, "event_type": body.event_type}),
        )
    )
    db.commit()

    detail = CaseDetail.model_validate(case)
    detail.contributing_factors = case.get_contributing_factors()
    return detail


@router.post("/{case_id}/deny", response_model=CaseDetail)
def deny(
    case_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> CaseDetail:
    case = db.query(RecoveryCase).filter_by(id=case_id, merchant_id=user.merchant_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case.recovery_status = "stopped"
    case.action_status = "denied"
    case.policy_decision = "denied"
    db.commit()

    # Record Human-in-the-Loop Audit Log
    db.add(
        AuditLog(
            merchant_id=user.merchant_id,
            actor="operator",
            action="case.denied",
            entity_type="recovery_case",
            entity_id=case.id,
            detail=json.dumps({"reason": "Operator rejected proposed recovery action"}),
        )
    )
    db.commit()

    detail = CaseDetail.model_validate(case)
    detail.contributing_factors = case.get_contributing_factors()
    return detail


@router.get("/{case_id}/timeline")
def timeline(case_id: int, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)) -> list[dict]:
    case = db.query(RecoveryCase).filter_by(id=case_id, merchant_id=user.merchant_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    events: list[dict] = []
    runs = db.query(AgentRun).filter_by(case_id=case_id, merchant_id=user.merchant_id).order_by(AgentRun.started_at).all()
    for r in runs:
        decisions = db.query(AgentDecision).filter_by(agent_run_id=r.id).all()
        for d in decisions:
            events.append({
                "ts": r.started_at.isoformat() if r.started_at else None,
                "agent": r.agent_name,
                "action": d.decision_type,
                "explanation": (d.get_output() or {}).get("note") or (d.get_output() or {}).get("rationale") or (d.get_output() or {}).get("diagnosis") or "",
                "status": r.status,
                "detail": d.get_output(),
            })
    calls = db.query(MCPToolCall).filter_by(case_id=case_id, merchant_id=user.merchant_id).order_by(MCPToolCall.created_at).all()
    for c in calls:
        events.append({
            "ts": c.created_at.isoformat() if c.created_at else None,
            "agent": "mcp",
            "action": c.tool_name,
            "explanation": f"MCP tool {c.tool_name} -> {c.status}",
            "status": c.status,
            "detail": c.get_result(),
        })
    # Sort by ts (None last).
    events.sort(key=lambda e: (e["ts"] is None, e["ts"] or ""))
    return events
