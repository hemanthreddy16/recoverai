"""Complete End-to-End Recovery Flow Test.

Tests the full sequential workflow:
FAILED PAYMENT
→ WEBHOOK INGESTION
→ RECOVERY CASE CREATION
→ DETECTION AGENT
→ DIAGNOSIS AGENT
→ ML PREDICTION AGENT (GradientBoosting)
→ STRATEGY AGENT
→ POLICY ENGINE
→ MCP TOOL INVOCATION
→ PAYMENT ACTION (Sandbox)
→ VERIFICATION AGENT
→ DATABASE & AUDIT LOG PERSISTENCE
→ DASHBOARD METRICS UPDATE
"""
from __future__ import annotations

import json
import uuid
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


def test_full_e2e_recovery_workflow(client: TestClient, auth_headers: dict):
    # -------------------------------------------------------------
    # 1. Capture baseline dashboard metrics
    # -------------------------------------------------------------
    dash_before = client.get("/api/v1/dashboard", headers=auth_headers).json()
    init_at_risk = dash_before["revenue_at_risk"]
    init_recovered = dash_before["revenue_recovered"]

    # -------------------------------------------------------------
    # 2. Simulate Razorpay payment.failed webhook event
    # -------------------------------------------------------------
    evt_id = f"evt_e2e_{uuid.uuid4().hex[:10]}"
    pay_id = f"pay_e2e_{uuid.uuid4().hex[:10]}"
    fail_amount = 3500.0  # ₹3,500

    webhook_payload = {
        "entity": "event",
        "account_id": "acc_e2e_test",
        "event": "payment.failed",
        "id": evt_id,
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": int(fail_amount * 100),  # paise
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "error_reason": "insufficient_funds",
                    "customer": {
                        "id": f"cust_e2e_{uuid.uuid4().hex[:8]}",
                        "name": "E2E Recovery User",
                        "email": "e2e.user@example.com",
                        "contact": "9876543210",
                    },
                }
            }
        },
    }

    wh_resp = client.post(
        "/api/v1/webhooks/razorpay",
        content=json.dumps(webhook_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    assert wh_resp.status_code == 200
    assert wh_resp.text == "ok"

    # -------------------------------------------------------------
    # 3. Verify case created and processed by agents
    # -------------------------------------------------------------
    cases_resp = client.get("/api/v1/cases?limit=10", headers=auth_headers)
    assert cases_resp.status_code == 200
    cases = cases_resp.json()
    assert len(cases) > 0

    # Locate the newly created case
    target_case = next((c for c in cases if c["amount_at_risk"] == fail_amount), cases[0])
    case_id = target_case["id"]

    # -------------------------------------------------------------
    # 4. Inspect Case Details & AI Decision Trace
    # -------------------------------------------------------------
    case_detail_resp = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers)
    assert case_detail_resp.status_code == 200
    detail = case_detail_resp.json()

    assert detail["amount_at_risk"] == fail_amount
    assert detail["failure_reason"] in ("insufficient_funds", "card_declined")
    # Prediction Agent ML output
    assert detail["recovery_probability"] is not None
    assert 0.0 <= detail["recovery_probability"] <= 1.0
    # Strategy Agent decision
    assert detail["recommended_action"] in (
        "retry_payment",
        "create_payment_link",
        "send_email",
        "send_whatsapp",
        "smart_retry",
        "payment_link",
        "email_reminder",
    )
    # Policy Engine status
    assert detail["policy_decision"] in ("auto", "approval")

    # -------------------------------------------------------------
    # 5. Check Case Audit Timeline
    # -------------------------------------------------------------
    tl_resp = client.get(f"/api/v1/cases/{case_id}/timeline", headers=auth_headers)
    assert tl_resp.status_code == 200
    timeline = tl_resp.json()
    assert len(timeline) >= 3
    agents_in_timeline = [t["agent"] for t in timeline]
    assert "detection" in agents_in_timeline
    assert "diagnosis" in agents_in_timeline

    # -------------------------------------------------------------
    # 6. Execute Recovery / Approval & Verification
    # -------------------------------------------------------------
    approve_resp = client.post(
        f"/api/v1/cases/{case_id}/approve",
        json={"simulated_outcome": "success"},
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200
    updated_case = approve_resp.json()
    assert updated_case["recovery_status"] == "recovered"
    assert updated_case["amount_recovered"] == fail_amount

    # -------------------------------------------------------------
    # 7. Verify Dashboard KPIs Updated Dynamically
    # -------------------------------------------------------------
    dash_after = client.get("/api/v1/dashboard", headers=auth_headers).json()
    assert dash_after["revenue_recovered"] >= init_recovered + fail_amount

    # -------------------------------------------------------------
    # 8. Verify Audit Log recorded the execution
    # -------------------------------------------------------------
    audit_resp = client.get("/api/v1/audit?limit=20", headers=auth_headers)
    assert audit_resp.status_code == 200
    audit_logs = audit_resp.json()
    assert any(log["entity_id"] == case_id or "case" in log["action"] for log in audit_logs)
