"""Recovery workflow, agent execution, MCP calls, notifications, audit, ML store."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RecoveryCase(Base):
    """A single revenue-at-risk case tracked through the agent pipeline."""

    __tablename__ = "recovery_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True
    )

    amount_at_risk: Mapped[float] = mapped_column(Float, nullable=False)
    # risk_score: 0..1 computed during detection.
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(120))
    detection_reason: Mapped[str | None] = mapped_column(Text)

    # Diagnosis agent outputs.
    diagnosis: Mapped[str | None] = mapped_column(Text)
    diagnosis_confidence: Mapped[float | None] = mapped_column(Float)
    contributing_factors: Mapped[str | None] = mapped_column(Text)  # JSON list
    recommended_recovery_category: Mapped[str | None] = mapped_column(String(60))

    # Prediction model outputs.
    recovery_probability: Mapped[float | None] = mapped_column(Float)
    model_version: Mapped[str | None] = mapped_column(String(40))

    # Strategy + Policy outputs.
    recommended_action: Mapped[str | None] = mapped_column(String(60))
    strategy_rationale: Mapped[str | None] = mapped_column(Text)
    approved_action: Mapped[str | None] = mapped_column(String(60))
    policy_decision: Mapped[str | None] = mapped_column(String(40))  # auto|approval|denied
    policy_reason: Mapped[str | None] = mapped_column(Text)

    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)

    # Lifecycle & State Machine.
    # stage: failed|diagnosed|recovery_recommended|approval_required|customer_approved|payment_link_created|retry_initiated|awaiting_payment|payment_processing|payment_success|payment_verified|recovered|stopped
    stage: Mapped[str] = mapped_column(String(50), default="failed", index=True)
    # action_status: pending|approved|executing|executed|failed
    action_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    # recovery_status: open|awaiting_payment|in_progress|recovered|failed|stopped
    recovery_status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    amount_recovered: Mapped[float] = mapped_column(Float, default=0.0)
    assigned_to: Mapped[int | None] = mapped_column(Integer)

    # Customer Interaction & Settlement Tracking
    whatsapp_status: Mapped[str] = mapped_column(String(30), default="not_dispatched")  # not_dispatched|sent|delivered|read|failed
    customer_response: Mapped[str] = mapped_column(String(30), default="pending")  # pending|opened_link|approved|rejected|paid
    payment_link_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_link_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verified_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

    def set_contributing_factors(self, factors: list[str]) -> None:
        self.contributing_factors = json.dumps(factors or [])

    def get_contributing_factors(self) -> list[str]:
        try:
            return json.loads(self.contributing_factors or "[]")
        except json.JSONDecodeError:
            return []


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[int] = mapped_column(
        ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(60), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), default="scheduled")
    detail: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    scheduled_time: Mapped[datetime | None] = mapped_column(DateTime)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime)
    result: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def set_detail(self, data: dict) -> None:
        self.detail = json.dumps(data or {})

    def get_detail(self) -> dict:
        try:
            return json.loads(self.detail or "{}")
        except json.JSONDecodeError:
            return {}

    def set_result(self, data: dict) -> None:
        self.result = json.dumps(data or {})

    def get_result(self) -> dict:
        try:
            return json.loads(self.result or "{}")
        except json.JSONDecodeError:
            return {}


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[int | None] = mapped_column(
        ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=True, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_run_id: Mapped[int] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[int | None] = mapped_column(
        ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=True, index=True
    )
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(60), nullable=False)
    decision_type: Mapped[str] = mapped_column(String(80), nullable=False)
    input_data: Mapped[str] = mapped_column(Text, default="{}")
    output_data: Mapped[str] = mapped_column(Text, default="{}")
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def set_input(self, data: dict) -> None:
        self.input_data = json.dumps(data or {})

    def set_output(self, data: dict) -> None:
        self.output_data = json.dumps(data or {})

    def get_input(self) -> dict:
        try:
            return json.loads(self.input_data or "{}")
        except json.JSONDecodeError:
            return {}

    def get_output(self) -> dict:
        try:
            return json.loads(self.output_data or "{}")
        except json.JSONDecodeError:
            return {}


class MCPToolCall(Base):
    """Every invocation of an MCP-controlled tool is logged for auditability."""

    __tablename__ = "mcp_tool_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[int | None] = mapped_column(
        ForeignKey("recovery_cases.id", ondelete="SET NULL"), nullable=True
    )
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    arguments: Mapped[str] = mapped_column(Text, default="{}")
    result: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(30), default="ok")  # ok|error|denied
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    caller: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def set_arguments(self, data: dict) -> None:
        self.arguments = json.dumps(data or {})

    def get_arguments(self) -> dict:
        try:
            return json.loads(self.arguments or "{}")
        except json.JSONDecodeError:
            return {}

    def set_result(self, data: dict) -> None:
        self.result = json.dumps(data or {})

    def get_result(self) -> dict:
        try:
            return json.loads(self.result or "{}")
        except json.JSONDecodeError:
            return {}


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    case_id: Mapped[int | None] = mapped_column(
        ForeignKey("recovery_cases.id", ondelete="SET NULL"), nullable=True
    )
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(60))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str] = mapped_column(Text, default="{}")
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def set_detail(self, data: dict) -> None:
        self.detail = json.dumps(data or {})


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[int | None] = mapped_column(
        ForeignKey("recovery_cases.id", ondelete="SET NULL"), nullable=True
    )
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"), nullable=True
    )
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    features: Mapped[str] = mapped_column(Text, default="{}")
    recovery_probability: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_label: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def set_features(self, data: dict) -> None:
        self.features = json.dumps(data or {})


class MerchantPolicy(Base):
    """Per-merchant guardrails enforced by the Policy Engine.

    The Policy Engine is the gatekeeper that prevents the LLM/agents from
    having unrestricted authority over financial operations.
    """

    __tablename__ = "merchant_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Probability at/above which a low-risk action is automatic (no approval).
    automatic_threshold: Mapped[float] = mapped_column(Float, default=0.55)
    # Probability at/below which escalation/denial strongly considered.
    approval_threshold: Mapped[float] = mapped_column(Float, default=0.4)
    # Maximum automatic retry attempts before requiring human approval.
    retry_limit: Mapped[int] = mapped_column(Integer, default=2)
    # Maximum total recovery attempts across all actions.
    max_recovery_attempts: Mapped[int] = mapped_column(Integer, default=3)
    # Amount (in currency units) above which a case is HIGH RISK -> human approval.
    high_value_threshold: Mapped[float] = mapped_column(Float, default=50000.0)
    # Whether agents may auto-run these action types.
    allow_auto_retry: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_auto_payment_link: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_auto_notification: Mapped[bool] = mapped_column(Boolean, default=True)
    # Notification channels enabled (JSON list): email, sms, whatsapp.
    notification_channels: Mapped[str] = mapped_column(String(200), default='["email"]')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    def get_channels(self) -> list[str]:
        try:
            return json.loads(self.notification_channels or "[]")
        except json.JSONDecodeError:
            return ["email"]

    def set_channels(self, channels: list[str]) -> None:
        self.notification_channels = json.dumps(channels or [])
