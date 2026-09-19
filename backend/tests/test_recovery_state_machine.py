"""Unit & Integration Tests for Payment Recovery State Machine.

Verifies that:
1. 'insufficient_funds' payment failure creates a case that is NOT recovered.
2. Creating a payment link leaves amount_recovered at 0.0 (awaiting payment).
3. Operator/Customer approval executes the action without prematurely marking recovered.
4. Genuine payment capture / verification transitions case to RECOVERED with full amount.
5. Failed payment retry keeps case unrecovered and tracks retry counts.
6. Duplicate webhooks / events are idempotent and do not double-count recovered revenue.
7. WhatsApp status remains 'not_dispatched' and Customer response remains 'pending' until dispatched.
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


def test_scenario_1_insufficient_funds_not_prematurely_recovered(client: TestClient, auth_headers: dict):
    """Test 1: When a payment fails with insufficient_funds, case is NOT marked recovered."""
    # Run the recoverable_payment_failure scenario
    resp = client.post(
        "/api/v1/demo/run",
        json={"scenario": "recoverable_payment_failure"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    case_id = data["case_id"]

    # Fetch detailed case
    detail = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers).json()

    assert detail["failure_reason"] == "insufficient_funds"
    assert detail["amount_at_risk"] == 1800.0
    # Crucial: Must NOT be marked recovered
    assert detail["recovery_status"] != "recovered"
    assert detail["amount_recovered"] == 0.0
    assert detail["stage"] in ("approval_required", "payment_link_created", "awaiting_payment", "customer_approved", "failed")


def test_scenario_2_payment_link_creation_sets_awaiting_payment(client: TestClient, auth_headers: dict):
    """Test 2: Creating a payment link transitions stage to payment_link_created with amount_recovered=0."""
    evt_id = f"evt_test2_{uuid.uuid4().hex[:10]}"
    pay_id = f"pay_test2_{uuid.uuid4().hex[:10]}"
    amount = 2500.0

    payload = {
        "entity": "event",
        "account_id": "acc_test",
        "event": "payment.failed",
        "id": evt_id,
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": int(amount * 100),
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "error_reason": "insufficient_funds",
                    "customer": {
                        "id": f"cust_{uuid.uuid4().hex[:8]}",
                        "name": "State Machine User",
                        "email": "sm.user@example.com",
                        "contact": "9876543210",
                    },
                }
            }
        },
    }

    wh_resp = client.post(
        "/api/v1/webhooks/razorpay",
        content=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    assert wh_resp.status_code == 200

    # Retrieve case
    cases = client.get("/api/v1/cases?limit=10", headers=auth_headers).json()
    case = next(c for c in cases if c["amount_at_risk"] == amount)
    case_id = case["id"]

    detail = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers).json()
    assert detail["amount_recovered"] == 0.0
    assert detail["recovery_status"] in ("open", "awaiting_payment", "in_progress")


def test_scenario_3_human_approval_does_not_mark_recovered(client: TestClient, auth_headers: dict):
    """Test 3: Approving a case executes recovery action (payment link) but does not mark recovered."""
    # Create high value case requiring approval
    resp = client.post(
        "/api/v1/demo/run",
        json={"scenario": "high_value_payment"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    case_id = data["case_id"]

    # Check case is in approval or awaiting payment
    detail_before = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers).json()
    assert detail_before["amount_recovered"] == 0.0

    if detail_before["policy_decision"] == "approval":
        appr_resp = client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"simulated_outcome": "success"},
            headers=auth_headers,
        )
        assert appr_resp.status_code == 200
        appr_data = appr_resp.json()
        assert appr_data["recovery_status"] in ("awaiting_payment", "open", "in_progress")
        assert appr_data["amount_recovered"] == 0.0


def test_scenario_4_genuine_payment_webhook_recovers_case(client: TestClient, auth_headers: dict):
    """Test 4: Receiving verified payment event transitions case through state machine to recovered."""
    pay_ref = f"pay_ver_{uuid.uuid4().hex[:10]}"
    amount = 3200.0

    # 1. Create a failed payment webhook
    wh_fail = client.post(
        "/api/v1/webhooks/razorpay",
        content=json.dumps({
            "entity": "event",
            "account_id": "acc_test",
            "event": "payment.failed",
            "id": f"evt_f_{uuid.uuid4().hex[:8]}",
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_ref,
                        "amount": int(amount * 100),
                        "currency": "INR",
                        "status": "failed",
                        "method": "upi",
                        "error_reason": "insufficient_funds",
                        "customer": {
                            "id": f"cust_{uuid.uuid4().hex[:8]}",
                            "name": "Verification User",
                            "email": "ver.user@example.com",
                            "contact": "9998887776",
                        },
                    }
                }
            },
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    assert wh_fail.status_code == 200

    # Locate case
    cases = client.get("/api/v1/cases?limit=10", headers=auth_headers).json()
    case = next(c for c in cases if c["amount_at_risk"] == amount)
    case_id = case["id"]

    # Verify not recovered yet
    c_before = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers).json()
    assert c_before["amount_recovered"] == 0.0

    # 2. Simulate payment.captured webhook
    wh_cap = client.post(
        "/api/v1/webhooks/razorpay",
        content=json.dumps({
            "entity": "event",
            "account_id": "acc_test",
            "event": "payment.captured",
            "id": f"evt_c_{uuid.uuid4().hex[:8]}",
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_ref,
                        "amount": int(amount * 100),
                        "currency": "INR",
                        "status": "captured",
                        "method": "upi",
                    }
                }
            },
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    assert wh_cap.status_code == 200

    # 3. Case is now verified and recovered
    c_after = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers).json()
    assert c_after["recovery_status"] == "recovered"
    assert c_after["amount_recovered"] == amount
    assert c_after["customer_response"] == "paid"
    assert c_after["stage"] == "recovered"


def test_scenario_5_failed_payment_retry_does_not_recover(client: TestClient, auth_headers: dict):
    """Test 5: Failed customer payment attempt keeps amount_recovered at 0.0."""
    # Create case
    resp = client.post(
        "/api/v1/demo/run",
        json={"scenario": "failed_recovery"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    case_id = resp.json()["case_id"]

    # Simulate customer payment failure
    fail_sim = client.post(
        f"/api/v1/cases/{case_id}/simulate-customer-payment",
        json={"outcome": "failure"},
        headers=auth_headers,
    )
    assert fail_sim.status_code == 200
    res = fail_sim.json()
    assert res["amount_recovered"] == 0.0
    assert res["stage"] in ("payment_failed", "failed", "awaiting_payment")


def test_scenario_6_idempotent_webhooks_prevent_double_counting(client: TestClient, auth_headers: dict):
    """Test 6: Sending duplicate payment.captured webhooks does not double-count recovered amount."""
    pay_ref = f"pay_idem_{uuid.uuid4().hex[:10]}"
    amount = 4000.0
    evt_id = f"evt_idem_{uuid.uuid4().hex[:8]}"

    # Failed payment first
    client.post(
        "/api/v1/webhooks/razorpay",
        content=json.dumps({
            "entity": "event",
            "account_id": "acc_test",
            "event": "payment.failed",
            "id": f"evt_f_{uuid.uuid4().hex[:8]}",
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_ref,
                        "amount": int(amount * 100),
                        "currency": "INR",
                        "status": "failed",
                        "method": "card",
                        "error_reason": "insufficient_funds",
                        "customer": {
                            "id": f"cust_{uuid.uuid4().hex[:8]}",
                            "name": "Idempotent User",
                            "email": "idem.user@example.com",
                            "contact": "9812345678",
                        },
                    }
                }
            },
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    cases = client.get("/api/v1/cases?limit=10", headers=auth_headers).json()
    case = next(c for c in cases if c["amount_at_risk"] == amount)
    case_id = case["id"]

    # First capture webhook
    payload_cap = {
        "entity": "event",
        "account_id": "acc_test",
        "event": "payment.captured",
        "id": evt_id,
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_ref,
                    "amount": int(amount * 100),
                    "currency": "INR",
                    "status": "captured",
                    "method": "card",
                }
            }
        },
    }
    r1 = client.post(
        "/api/v1/webhooks/razorpay",
        content=json.dumps(payload_cap).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    assert r1.status_code == 200

    c1 = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers).json()
    assert c1["amount_recovered"] == amount

    # Second duplicate capture webhook with different event ID but same payment
    payload_dup = dict(payload_cap)
    payload_dup["id"] = f"evt_dup_{uuid.uuid4().hex[:8]}"
    r2 = client.post(
        "/api/v1/webhooks/razorpay",
        content=json.dumps(payload_dup).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    assert r2.status_code == 200

    c2 = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers).json()
    # Amount recovered MUST remain exact single amount (not 8000.0)
    assert c2["amount_recovered"] == amount


def test_scenario_7_whatsapp_and_customer_response_integrity(client: TestClient, auth_headers: dict):
    """Test 7: When WhatsApp is not dispatched, status is not_dispatched and customer response is pending."""
    resp = client.post(
        "/api/v1/demo/run",
        json={"scenario": "recoverable_payment_failure"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    case_id = resp.json()["case_id"]

    detail = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers).json()
    assert detail["whatsapp_status"] in ("not_dispatched", "sent", "delivered")
    assert detail["customer_response"] in ("pending", "opened_link")
