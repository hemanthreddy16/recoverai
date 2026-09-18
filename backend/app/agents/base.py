"""Agent base infrastructure: execution context, run + decision logging.

Every agent records an AgentRun (start/finish) and an AgentDecision (inputs,
outputs, confidence) so the full reasoning trail is auditable on the dashboard.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.logging_setup import logger
from app.models.recovery import AgentDecision, AgentRun
from app.services.llm import LLMService
from app.mcp.gateway import MCPGateway


class AgentContext:
    def __init__(
        self,
        db: Session,
        merchant_id: int,
        llm: LLMService,
        gateway: MCPGateway,
    ):
        self.db = db
        self.merchant_id = merchant_id
        self.llm = llm
        self.gateway = gateway

    def start_run(self, agent_name: str, case_id: int | None = None) -> AgentRun:
        run = AgentRun(merchant_id=self.merchant_id, agent_name=agent_name, case_id=case_id, status="running")
        run.started_at = datetime.now(timezone.utc)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def finish_run(self, run: AgentRun, status: str = "success", error: str | None = None) -> None:
        run.status = status
        run.finished_at = datetime.now(timezone.utc)
        run.error = error
        self.db.commit()

    def record_decision(
        self,
        run: AgentRun,
        decision_type: str,
        input_data: dict,
        output_data: dict,
        confidence: float | None = None,
    ) -> AgentDecision:
        d = AgentDecision(
            agent_run_id=run.id,
            case_id=run.case_id,
            merchant_id=self.merchant_id,
            agent_name=run.agent_name,
            decision_type=decision_type,
        )
        d.set_input(input_data)
        d.set_output(output_data)
        d.confidence = confidence
        self.db.add(d)
        self.db.commit()
        return d


class BaseAgent:
    name = "base"

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    def _ask_llm(self, system: str, user: str, max_tokens: int = 600) -> str | None:
        try:
            if self.ctx.llm.enabled:
                return self.ctx.llm.complete(system, user, max_tokens)
        except Exception as e:  # pragma: no cover
            logger.warning("%s LLM call failed, using heuristic: %s", self.name, e)
        return None
