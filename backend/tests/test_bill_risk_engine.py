"""Unit and integration tests for AI Payment Risk Prediction Engine."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.bill_risk_engine import BillRiskEngine


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_context(client: TestClient):
    email = f"risk_admin_{id(client)}@test.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "merchant_name": "Risk Engine Test Merchant",
            "full_name": "Risk Evaluator",
            "role": "admin",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "merchant_id": resp.json()["user"]["merchant_id"],
    }


def test_classify_risk_level_thresholds():
    assert BillRiskEngine.classify_risk_level(0) == "Low"
    assert BillRiskEngine.classify_risk_level(30) == "Low"
    assert BillRiskEngine.classify_risk_level(31) == "Medium"
    assert BillRiskEngine.classify_risk_level(70) == "Medium"
    assert BillRiskEngine.classify_risk_level(71) == "High"
    assert BillRiskEngine.classify_risk_level(100) == "High"


def test_create_bill_with_ai_risk_score(client: TestClient, auth_context: dict):
    headers = auth_context["headers"]
    now = datetime.now(timezone.utc)

    # 1. High risk overdue EMI
    resp = client.post(
        "/api/v1/bills",
        headers=headers,
        json={
            "name": "Tata Capital Machinery Loan EMI",
            "category": "EMI",
            "amount": 95000.0,
            "due_date": (now - timedelta(days=5)).isoformat(),
            "recurrence": "Monthly",
            "customer_name": "Suresh Raina",
            "customer_phone": "9811998877",
            "notes": "Large industrial equipment loan",
        },
    )
    assert resp.status_code == 201, resp.text
    b = resp.json()
    assert 0 <= b["risk_score"] <= 100
    assert b["risk_level"] == "High"
    assert b["risk_score"] >= 71
    assert "overdue" in b["risk_reason"].lower() or "large" in b["risk_reason"].lower()
    assert len(b["risk_factors"]) >= 2
    assert len(b["risk_history"]) >= 1

    # 2. Low risk utility bill in future
    resp2 = client.post(
        "/api/v1/bills",
        headers=headers,
        json={
            "name": "Reliance Jio Office Wifi",
            "category": "Internet",
            "amount": 1499.0,
            "due_date": (now + timedelta(days=20)).isoformat(),
            "recurrence": "Monthly",
            "customer_name": "Anita Roy",
            "customer_phone": "9822114455",
        },
    )
    assert resp2.status_code == 201, resp2.text
    b2 = resp2.json()
    assert b2["risk_score"] <= 30
    assert b2["risk_level"] == "Low"


def test_recalculate_risk_endpoints(client: TestClient, auth_context: dict):
    headers = auth_context["headers"]
    now = datetime.now(timezone.utc)

    # Create bill
    create_resp = client.post(
        "/api/v1/bills",
        headers=headers,
        json={
            "name": "Commercial Office Lease",
            "category": "Rent",
            "amount": 40000.0,
            "due_date": (now + timedelta(days=1)).isoformat(),
            "customer_name": "Leaseholder Inc",
            "customer_phone": "9833221100",
        },
    )
    assert create_resp.status_code == 201
    bill_id = create_resp.json()["id"]

    # Recalculate single risk
    recalc_resp = client.post(f"/api/v1/bills/{bill_id}/recalculate-risk", headers=headers)
    assert recalc_resp.status_code == 200
    r_data = recalc_resp.json()
    assert r_data["risk_score"] >= 0
    assert len(r_data["risk_history"]) >= 2

    # Batch recalculate all
    batch_resp = client.post("/api/v1/bills/recalculate-all-risk", headers=headers)
    assert batch_resp.status_code == 200
    assert batch_resp.json()["status"] == "success"
    assert batch_resp.json()["recalculated_count"] >= 1


def test_summary_includes_risk_summary(client: TestClient, auth_context: dict):
    headers = auth_context["headers"]
    resp = client.get("/api/v1/bills/summary", headers=headers)
    assert resp.status_code == 200
    s = resp.json()
    assert "risk_summary" in s
    rs = s["risk_summary"]
    assert "high_risk_count" in rs
    assert "medium_risk_count" in rs
    assert "low_risk_count" in rs
    assert "total_amount_at_risk" in rs
    assert "average_risk_score" in rs
    assert "top_risk_reasons" in rs
