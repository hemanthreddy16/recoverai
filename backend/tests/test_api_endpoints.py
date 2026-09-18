"""Comprehensive test suite for Phase 3:
FastAPI API endpoints, authentication, JWT tokens, RBAC, merchant isolation,
customers, payments, recovery cases, analytics, agents, and audit logs.
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
def auth_context(client: TestClient):
    # Register a new merchant and admin
    email = f"admin_phase3_{id(client)}@test.com"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "merchant_name": "Phase3 Store",
            "full_name": "Phase3 Admin",
            "role": "admin",
        },
    )
    assert reg_resp.status_code == 201, reg_resp.text
    token = reg_resp.json()["access_token"]
    user_id = reg_resp.json()["user"]["id"]
    merchant_id = reg_resp.json()["user"]["merchant_id"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": user_id,
        "merchant_id": merchant_id,
        "email": email,
    }


@pytest.fixture(scope="session")
def other_merchant_context(client: TestClient):
    # Register a second merchant to verify tenant isolation
    email = f"other_store_{id(client)}@test.com"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "merchant_name": "Second Merchant Ltd",
            "full_name": "Other Admin",
            "role": "admin",
        },
    )
    assert reg_resp.status_code == 201, reg_resp.text
    token = reg_resp.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "merchant_id": reg_resp.json()["user"]["merchant_id"],
        "email": email,
    }


# =====================================================================
# 1. Authentication & JWT Tests
# =====================================================================
def test_auth_login_success(client: TestClient, auth_context: dict):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": auth_context["email"], "password": "Password123!"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["user"]["email"] == auth_context["email"]


def test_auth_login_invalid_password(client: TestClient, auth_context: dict):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": auth_context["email"], "password": "wrong_password"},
    )
    assert resp.status_code == 401


def test_auth_me_endpoint(client: TestClient, auth_context: dict):
    resp = client.get("/api/v1/auth/me", headers=auth_context["headers"])
    assert resp.status_code == 200
    assert resp.json()["email"] == auth_context["email"]


def test_unauthenticated_request_fails(client: TestClient):
    resp = client.get("/api/v1/customers")
    assert resp.status_code in (401, 403)


# =====================================================================
# 2. Customer APIs & Merchant Isolation
# =====================================================================
def test_customer_lifecycle_and_isolation(client: TestClient, auth_context: dict, other_merchant_context: dict):
    # Create customer under Merchant A
    cust_data = {
        "external_id": "CUST-API-001",
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "phone": "9876543210",
        "clv": 15000.0,
    }
    resp = client.post("/api/v1/customers", json=cust_data, headers=auth_context["headers"])
    assert resp.status_code == 201
    cust_id = resp.json()["id"]
    assert resp.json()["external_id"] == "CUST-API-001"

    # Get customer by ID (Merchant A)
    get_resp = client.get(f"/api/v1/customers/{cust_id}", headers=auth_context["headers"])
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Jane Doe"

    # Update customer (Merchant A)
    update_resp = client.patch(
        f"/api/v1/customers/{cust_id}",
        json={"name": "Jane Smith", "clv": 18000.0},
        headers=auth_context["headers"],
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Jane Smith"
    assert update_resp.json()["clv"] == 18000.0

    # Merchant Isolation check: Merchant B cannot access Merchant A's customer
    other_get = client.get(f"/api/v1/customers/{cust_id}", headers=other_merchant_context["headers"])
    assert other_get.status_code == 404

    # List customers for Merchant A
    list_resp = client.get("/api/v1/customers?q=Jane", headers=auth_context["headers"])
    assert list_resp.status_code == 200
    assert any(c["id"] == cust_id for c in list_resp.json())


# =====================================================================
# 3. Payment APIs & Failure Ingestion
# =====================================================================
def test_payment_creation_and_listing(client: TestClient, auth_context: dict):
    # Create customer first
    cust_resp = client.post(
        "/api/v1/customers",
        json={"external_id": "CUST-PAY-001", "name": "Payment User", "email": "pay@example.com"},
        headers=auth_context["headers"],
    )
    cust_id = cust_resp.json()["id"]

    # Record failed payment
    pay_data = {
        "customer_id": cust_id,
        "amount": 4200.0,
        "currency": "INR",
        "status": "failed",
        "failure_reason": "insufficient_funds",
        "payment_method": "upi",
    }
    pay_resp = client.post("/api/v1/payments", json=pay_data, headers=auth_context["headers"])
    assert pay_resp.status_code == 201
    pay_id = pay_resp.json()["id"]
    assert pay_resp.json()["amount"] == 4200.0

    # Get payment by ID
    get_pay = client.get(f"/api/v1/payments/{pay_id}", headers=auth_context["headers"])
    assert get_pay.status_code == 200
    assert get_pay.json()["failure_reason"] == "insufficient_funds"

    # List payments with filters
    list_pay = client.get("/api/v1/payments?status=failed", headers=auth_context["headers"])
    assert list_pay.status_code == 200
    assert any(p["id"] == pay_id for p in list_pay.json())


# =====================================================================
# 4. Recovery Case APIs, Approval, Denial, Timeline
# =====================================================================
def test_recovery_case_workflow(client: TestClient, auth_context: dict):
    # Create customer
    cust_resp = client.post(
        "/api/v1/customers",
        json={"external_id": "CUST-CASE-001", "name": "Case User", "email": "case@test.com"},
        headers=auth_context["headers"],
    )
    cust_id = cust_resp.json()["id"]

    # Create Case
    case_resp = client.post(
        "/api/v1/cases",
        json={
            "customer_id": cust_id,
            "amount_at_risk": 5500.0,
            "event_type": "failed_payment",
            "failure_reason": "card_declined",
        },
        headers=auth_context["headers"],
    )
    assert case_resp.status_code == 201
    case_id = case_resp.json()["id"]
    assert case_resp.json()["amount_at_risk"] == 5500.0
    assert case_resp.json()["recovery_status"] == "open"

    # Fetch Case Detail
    detail_resp = client.get(f"/api/v1/cases/{case_id}", headers=auth_context["headers"])
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == case_id

    # Fetch Timeline
    timeline_resp = client.get(f"/api/v1/cases/{case_id}/timeline", headers=auth_context["headers"])
    assert timeline_resp.status_code == 200
    assert isinstance(timeline_resp.json(), list)

    # Deny / Stop Recovery
    deny_resp = client.post(f"/api/v1/cases/{case_id}/deny", headers=auth_context["headers"])
    assert deny_resp.status_code == 200
    assert deny_resp.json()["recovery_status"] == "stopped"
    assert deny_resp.json()["policy_decision"] == "denied"


# =====================================================================
# 5. Analytics & Dashboard APIs
# =====================================================================
def test_analytics_and_dashboard_apis(client: TestClient, auth_context: dict):
    dash_resp = client.get("/api/v1/dashboard", headers=auth_context["headers"])
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert "revenue_at_risk" in dash_data
    assert "recovery_rate" in dash_data

    rec_resp = client.get("/api/v1/analytics/recovery", headers=auth_context["headers"])
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    assert "total_cases" in rec_data

    model_resp = client.get("/api/v1/analytics/model", headers=auth_context["headers"])
    assert model_resp.status_code == 200
    assert "model_type" in model_resp.json()


# =====================================================================
# 6. Agent APIs & Summary
# =====================================================================
def test_agent_apis(client: TestClient, auth_context: dict):
    activity_resp = client.get("/api/v1/agents/activity?limit=10", headers=auth_context["headers"])
    assert activity_resp.status_code == 200
    assert isinstance(activity_resp.json(), list)

    summary_resp = client.get("/api/v1/agents/summary", headers=auth_context["headers"])
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert "detection" in summary
    assert "diagnosis" in summary
    assert "prediction" in summary


# =====================================================================
# 7. Audit Log APIs
# =====================================================================
def test_audit_log_apis(client: TestClient, auth_context: dict):
    audit_resp = client.get("/api/v1/audit?limit=10", headers=auth_context["headers"])
    assert audit_resp.status_code == 200
    assert isinstance(audit_resp.json(), list)
