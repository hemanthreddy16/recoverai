"""Test suite for RESURGE V2 Upgrade features:
- AI Command Center queries and action triggers
- Agent statistics & control center telemetry
- MCP registry and sandbox tool test execution
- Extended analytics with 30-day forecast and customer segments
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers(client: TestClient):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@recoverai.dev", "password": "recoverai123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# =====================================================================
# 1. AI Command Center Tests
# =====================================================================
def test_command_query_revenue_overview(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/api/v1/command/query",
        json={"query": "How much revenue is currently at risk?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "revenue_overview"
    assert "revenue_at_risk" in data["data"]
    assert "predicted_recoverable" in data["data"]


def test_command_query_high_value_cases(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/api/v1/command/query",
        json={"query": "Show me all high-value failed payments"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "high_value_cases"
    assert "cases" in data["data"]


def test_command_query_strategy_performance(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/api/v1/command/query",
        json={"query": "Which recovery strategy performs best?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "strategy_performance"


def test_command_query_case_explanation(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/api/v1/command/query",
        json={"query": "Why did case #1 fail?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "case_explain"


# =====================================================================
# 2. Multi-Agent Control Center Telemetry
# =====================================================================
def test_agent_stats_endpoint(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/agents/stats", headers=auth_headers)
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) == 8
    agent_names = [a["name"] for a in agents]
    for expected in ("detection", "diagnosis", "prediction", "strategy", "policy", "recovery", "verification", "analytics"):
        assert expected in agent_names


# =====================================================================
# 3. MCP Tool Registry & Sandbox Tester
# =====================================================================
def test_mcp_registry_endpoint(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/mcp/registry", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "servers" in data
    assert len(data["servers"]) >= 3


def test_mcp_test_tool_sandbox(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/api/v1/mcp/test-tool",
        json={"tool_name": "get_customer", "arguments": {"customer_id": 1}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool_name"] == "get_customer"
    assert data["status"] == "ok"
    assert "result" in data


# =====================================================================
# 4. Extended Analytics & 30-Day Forecast
# =====================================================================
def test_analytics_forecast_and_segments(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/analytics/recovery", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "forecast_30d" in data
    assert "today" in data["forecast_30d"]
    assert "day_30" in data["forecast_30d"]
    assert "recovery_by_segment" in data
