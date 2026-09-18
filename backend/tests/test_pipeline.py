"""RecoverAI comprehensive test suite."""
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
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_root(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "name" in resp.json()


def test_root_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"


def test_api_v1_health(client: TestClient):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_auth_me(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "demo@recoverai.dev"


def test_dashboard_metrics(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "recovery_rate" in data
    assert "revenue_at_risk" in data


def test_analytics(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/analytics/recovery", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_cases" in data
    assert "recovery_by_failure_type" in data

    resp_model = client.get("/api/v1/analytics/model", headers=auth_headers)
    assert resp_model.status_code == 200
    data_model = resp_model.json()
    assert "model_type" in data_model


def test_demo_scenarios(client: TestClient, auth_headers: dict):
    scenarios = [
        "simple_payment_failure",
        "recoverable_payment_failure",
        "repeated_payment_failure",
        "high_value_payment",
        "checkout_abandonment",
        "subscription_failure",
        "failed_recovery",
        "successful_recovery",
    ]
    for sc in scenarios:
        resp = client.post("/api/v1/demo/run", json={"scenario": sc}, headers=auth_headers)
        assert resp.status_code == 200, f"Scenario {sc} failed: {resp.text}"
        data = resp.json()
        assert "case_id" in data
        assert "recovery_status" in data


def test_cases_list_and_detail(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/cases?limit=10", headers=auth_headers)
    assert resp.status_code == 200
    cases = resp.json()
    assert isinstance(cases, list)
    if cases:
        case_id = cases[0]["id"]
        detail_resp = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["id"] == case_id

        timeline_resp = client.get(f"/api/v1/cases/{case_id}/timeline", headers=auth_headers)
        assert timeline_resp.status_code == 200
        assert isinstance(timeline_resp.json(), list)


def test_settings(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/settings/policy", headers=auth_headers)
    assert resp.status_code == 200
    policy = resp.json()
    assert "automatic_threshold" in policy
