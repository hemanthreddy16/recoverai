"""API schemas for cases, dashboard, analytics, agents, MCP, settings, demo."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator
import json


# ---------------- cases ----------------
class CaseOut(BaseModel):
    id: int
    customer_id: int
    payment_id: int | None
    amount_at_risk: float
    risk_score: float
    event_type: str
    failure_reason: str | None
    recovery_probability: float | None
    recommended_action: str | None
    approved_action: str | None
    policy_decision: str | None
    action_status: str
    recovery_status: str
    amount_recovered: float
    created_at: datetime | None

    model_config = {"from_attributes": True}


class CaseDetail(CaseOut):
    diagnosis: str | None
    diagnosis_confidence: float | None
    contributing_factors: list[str] = []
    strategy_rationale: str | None
    policy_reason: str | None
    model_version: str | None
    resolved_at: datetime | None

    @field_validator("contributing_factors", mode="before")
    @classmethod
    def _parse_factors(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
            except Exception:
                return [v] if v else []
        if isinstance(v, list):
            return [str(x) for x in v]
        return []


class ApproveRequest(BaseModel):
    simulated_outcome: str | None = "success"  # success | failure (demo only)


# ---------------- dashboard ----------------
class DashboardMetrics(BaseModel):
    revenue_at_risk: float
    revenue_recovered: float
    recovery_rate: float
    active_cases: int
    failed_payments: int
    checkout_abandonments: int
    subscription_failures: int
    predicted_recoverable: float = 0.0
    high_risk_customers_count: int = 0
    recovery_trend: list[dict[str, Any]] = []
    recent_pipeline_runs: list[dict[str, Any]] = []
    high_risk_cases: list[dict[str, Any]] = []


# ---------------- analytics ----------------
class AnalyticsOut(BaseModel):
    total_cases: int
    recovered_cases: int
    failed_cases: int
    open_cases: int
    stopped_cases: int
    recovery_rate: float
    total_revenue_recovered: float
    revenue_at_risk: float
    failed_recovery_amount: float
    agent_success_rate: float
    recovery_by_failure_type: dict[str, Any] = {}
    recovery_by_strategy: dict[str, Any] = {}
    recovery_by_segment: dict[str, Any] = {}
    forecast_30d: dict[str, Any] = {}


class MLMetricsOut(BaseModel):
    model_type: str = ""
    version: str = ""
    dataset_size: int = 0
    threshold: float = 0.5
    train: dict[str, Any] = {}
    validation: dict[str, Any] = {}
    test: dict[str, Any] = {}


# ---------------- agents ----------------
class AgentRunOut(BaseModel):
    id: int
    agent_name: str
    case_id: int | None
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None

    model_config = {"from_attributes": True}


class AgentDecisionOut(BaseModel):
    id: int
    agent_run_id: int
    agent_name: str
    decision_type: str
    confidence: float | None
    input_data: dict[str, Any] = {}
    output_data: dict[str, Any] = {}
    created_at: datetime | None

    model_config = {"from_attributes": True}


class AgentStats(BaseModel):
    name: str
    title: str
    status: str
    current_task: str
    last_action: str
    execution_count: int
    success_rate: float
    avg_duration_ms: float
    current_case_id: int | None = None
    last_run_at: datetime | None = None


# ---------------- mcp ----------------
class MCPToolCallOut(BaseModel):
    id: int
    case_id: int | None
    tool_name: str
    arguments: dict[str, Any] = {}
    result: dict[str, Any] = {}
    status: str
    duration_ms: int | None
    error: str | None
    caller: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class MCPToolTestRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = {}


class MCPToolTestResponse(BaseModel):
    tool_name: str
    status: str
    duration_ms: int
    result: dict[str, Any]
    error: str | None = None


# ---------------- command center ----------------
class CommandQueryRequest(BaseModel):
    query: str


class CommandQueryResponse(BaseModel):
    query: str
    intent: str
    answer: str
    data: dict[str, Any] = {}
    suggested_actions: list[dict[str, Any]] = []



# ---------------- settings ----------------
class PolicyUpdate(BaseModel):
    automatic_threshold: float | None = None
    approval_threshold: float | None = None
    retry_limit: int | None = None
    max_recovery_attempts: int | None = None
    high_value_threshold: float | None = None
    allow_auto_retry: bool | None = None
    allow_auto_payment_link: bool | None = None
    allow_auto_notification: bool | None = None
    notification_channels: list[str] | None = None


# ---------------- demo ----------------
class DemoScenarioRequest(BaseModel):
    scenario: str  # see demo router for valid values
    simulated_outcome: str | None = None  # override outcome for deterministic demos


class DemoResult(BaseModel):
    case_id: int
    event_type: str
    amount_at_risk: float
    recovery_probability: float | None
    recommended_action: str | None
    policy_decision: str | None
    approved_action: str | None
    recovery_status: str
    amount_recovered: float


# ---------------- customers ----------------
class CustomerCreate(BaseModel):
    external_id: str
    name: str = ""
    email: str = ""
    phone: str = ""
    clv: float = 0.0


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    clv: float | None = None


class CustomerOut(BaseModel):
    id: int
    merchant_id: int
    external_id: str
    name: str
    email: str
    phone: str
    clv: float
    created_at: datetime | None

    model_config = {"from_attributes": True}


# ---------------- payments ----------------
class PaymentCreate(BaseModel):
    customer_id: int
    amount: float
    currency: str = "INR"
    status: str = "failed"
    failure_reason: str | None = None
    payment_method: str | None = "card"


class PaymentOut(BaseModel):
    id: int
    merchant_id: int
    customer_id: int
    order_id: int | None = None
    subscription_id: int | None = None
    razorpay_payment_id: str | None = None
    razorpay_order_id: str | None = None
    amount: float
    currency: str
    status: str
    failure_reason: str | None
    payment_method: str | None
    created_at: datetime | None
    captured_at: datetime | None

    model_config = {"from_attributes": True}


# ---------------- audit ----------------
class AuditLogOut(BaseModel):
    id: int
    merchant_id: int
    actor: str
    action: str
    entity_type: str | None
    entity_id: int | None
    detail: dict[str, Any] = {}
    ip_address: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}

    @field_validator("detail", mode="before")
    @classmethod
    def _parse_detail(cls, v: Any) -> dict[str, Any]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {"raw": v}
        if isinstance(v, dict):
            return v
        return {}


# ---------------- case creation ----------------
class CaseCreate(BaseModel):
    customer_id: int
    payment_id: int | None = None
    amount_at_risk: float
    event_type: str = "failed_payment"
    failure_reason: str | None = None


# ---------------- ML prediction ----------------
class PredictRequest(BaseModel):
    transaction_amount: float = 5000.0
    customer_success_rate: float = 0.6
    customer_clv: float = 15000.0
    previous_failures: int = 1
    retry_count: int = 0
    payment_method: str = "card"
    failure_reason: str = "insufficient_funds"
    subscription_age_days: int = 90
    days_since_last_success: int = 5
    event_type: str = "payment_failed"


class PredictResponse(BaseModel):
    recovery_probability: float
    will_recover: bool
    model_version: str
    threshold: float
    features_used: dict[str, Any] = {}


class TrainResponse(BaseModel):
    status: str
    model_version: str
    dataset_size: int
    threshold: float
    train: dict[str, Any] = {}
    validation: dict[str, Any] = {}
    test: dict[str, Any] = {}

