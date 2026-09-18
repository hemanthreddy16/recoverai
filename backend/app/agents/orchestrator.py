"""Agent Orchestrator.

Runs the recovery pipeline in order:

  Detection -> Diagnosis -> Prediction -> Strategy -> Policy -> Recovery -> Verification

Detection is performed when an event arrives (webhook / demo). This orchestrator
takes an already-created case and drives it through the remaining agents, honouring
the Policy Engine gate (no automatic financial action without approval).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.analytics import AnalyticsAgent
from app.agents.base import AgentContext
from app.agents.diagnosis import DiagnosisAgent
from app.agents.policy import PolicyEngine
from app.agents.prediction import PredictionAgent
from app.agents.recovery import RecoveryAgent
from app.agents.strategy import StrategyAgent
from app.agents.verification import VerificationAgent
from app.logging_setup import logger
from app.mcp.gateway import MCPGateway
from app.models.recovery import MerchantPolicy, RecoveryCase
from app.services.llm import get_llm


def _policy(db: Session, merchant_id: int) -> MerchantPolicy:
    p = db.query(MerchantPolicy).filter_by(merchant_id=merchant_id).first()
    if p is None:
        p = MerchantPolicy(merchant_id=merchant_id)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def process_case(
    db: Session,
    case: RecoveryCase,
    simulated_outcome: str | None = None,
    auto_approve: bool = False,
) -> RecoveryCase:
    """Full pipeline for a case created by the Detection Agent."""
    merchant_id = case.merchant_id
    llm = get_llm()
    gateway = MCPGateway(db, merchant_id, caller="orchestrator")
    ctx = AgentContext(db, merchant_id, llm, gateway)
    policy = _policy(db, merchant_id)

    # 1) Diagnosis
    case = DiagnosisAgent(ctx).run(case)
    # 2) Prediction (real ML)
    case = PredictionAgent(ctx).run(case)
    # 3) Strategy
    case = StrategyAgent(ctx).run(case, policy)
    # 4) Policy
    case = PolicyEngine(ctx).evaluate(case, policy)

    decision = case.policy_decision
    if decision == "denied":
        logger.info("Case %s denied by policy", case.id)
        case.action_status = "failed"
        case.recovery_status = "stopped"
        db.commit()
        return case

    if decision == "auto" or (decision == "approval" and auto_approve):
        recovery = RecoveryAgent(ctx).execute(case)
        # 5) Verification (skip for intentionally stopped cases).
        if case.approved_action != "stop_recovery":
            case = VerificationAgent(ctx).run(case, simulated_outcome=simulated_outcome)
    else:
        # Awaiting human approval.
        logger.info("Case %s pending human approval", case.id)
        db.commit()
    return case


def approve_case(
    db: Session, case: RecoveryCase, simulated_outcome: str | None = None
) -> RecoveryCase:
    """Human approves a case that was gated for approval."""
    if case.policy_decision != "approval":
        return case
    case.approved_action = case.approved_action or case.recommended_action
    db.commit()
    merchant_id = case.merchant_id
    llm = get_llm()
    gateway = MCPGateway(db, merchant_id, caller="orchestrator")
    ctx = AgentContext(db, merchant_id, llm, gateway)
    case = RecoveryAgent(ctx).execute(case)
    case = VerificationAgent(ctx).run(case, simulated_outcome=simulated_outcome)
    return case


def compute_analytics(db: Session, merchant_id: int) -> dict:
    return AnalyticsAgent(db, merchant_id).compute()
