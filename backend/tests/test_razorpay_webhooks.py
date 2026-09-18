"""Razorpay Test Mode & Webhook Ingestion Tests.

Tests:
- payment.failed
- payment.captured
- order.paid
- Signature validation
- Idempotent deduplication
- Webhook simulation endpoint
"""
from __future__ import annotations

import json
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.razorpay_client import razorpay_client


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


def test_razorpay_client_simulation_mode():
    # Verify local simulation creates structured order and links
    order = razorpay_client.create_order(amount=2500.0, currency="INR", receipt="rcpt_101")
    assert order["amount"] == 250000
    assert order["currency"] == "INR"
    assert "id" in order


def test_webhook_signature_generation_and_verification():
    payload = b'{"event":"payment.failed","id":"evt_sig_123"}'
    secret = "test_webhook_secret_key_12345"
    sig = razorpay_client.generate_webhook_signature(payload, secret)
    assert isinstance(sig, str) and len(sig) == 64

    # Verify matching
    import hmac, hashlib
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert sig == expected


def test_webhook_payment_failed_ingestion(client: TestClient):
    event_id = f"evt_fail_{uuid.uuid4().hex[:10]}"
    pay_id = f"pay_fail_{uuid.uuid4().hex[:10]}"
    payload = {
        "entity": "event",
        "account_id": "acc_test",
        "event": "payment.failed",
        "id": event_id,
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": 480000,
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "error_reason": "insufficient_funds",
                    "customer": {
                        "id": f"cust_rz_{uuid.uuid4().hex[:6]}",
                        "name": "Webhook Tester",
                        "email": "webhook.tester@example.com",
                        "contact": "9876543210",
                    },
                }
            }
        },
    }

    body = json.dumps(payload).encode("utf-8")
    resp = client.post(
        "/api/v1/webhooks/razorpay",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.text == "ok"


def test_webhook_idempotency(client: TestClient):
    event_id = f"evt_idemp_{uuid.uuid4().hex[:10]}"
    payload = {
        "entity": "event",
        "event": "payment.failed",
        "id": event_id,
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_{uuid.uuid4().hex[:8]}",
                    "amount": 120000,
                    "currency": "INR",
                    "status": "failed",
                    "error_reason": "card_declined",
                }
            }
        },
    }
    body = json.dumps(payload).encode("utf-8")

    # First attempt -> ok
    resp1 = client.post("/api/v1/webhooks/razorpay", content=body, headers={"Content-Type": "application/json"})
    assert resp1.status_code == 200
    assert resp1.text == "ok"

    # Second attempt with same event id -> idempotent skip
    resp2 = client.post("/api/v1/webhooks/razorpay", content=body, headers={"Content-Type": "application/json"})
    assert resp2.status_code == 200
    assert "already processed" in resp2.text


def test_webhook_payment_captured(client: TestClient):
    event_id = f"evt_cap_{uuid.uuid4().hex[:10]}"
    pay_id = f"pay_cap_{uuid.uuid4().hex[:10]}"
    payload = {
        "entity": "event",
        "event": "payment.captured",
        "id": event_id,
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": 540000,
                    "currency": "INR",
                    "status": "captured",
                    "method": "upi",
                }
            }
        },
    }
    body = json.dumps(payload).encode("utf-8")
    resp = client.post("/api/v1/webhooks/razorpay", content=body, headers={"Content-Type": "application/json"})
    assert resp.status_code == 200
    assert resp.text == "ok"


def test_webhook_order_paid(client: TestClient):
    event_id = f"evt_order_{uuid.uuid4().hex[:10]}"
    order_id = f"order_paid_{uuid.uuid4().hex[:10]}"
    payload = {
        "entity": "event",
        "event": "order.paid",
        "id": event_id,
        "payload": {
            "order": {
                "entity": {
                    "id": order_id,
                    "amount": 320000,
                    "currency": "INR",
                    "status": "paid",
                }
            }
        },
    }
    body = json.dumps(payload).encode("utf-8")
    resp = client.post("/api/v1/webhooks/razorpay", content=body, headers={"Content-Type": "application/json"})
    assert resp.status_code == 200
    assert resp.text == "ok"


def test_webhook_simulator_endpoint(client: TestClient, auth_headers: dict):
    # 1. Simulate payment.failed
    resp_failed = client.post(
        "/api/v1/webhooks/simulate",
        json={
            "event_type": "payment.failed",
            "amount": 6200.0,
            "failure_reason": "network_error",
            "customer_name": "Simulated User",
            "customer_email": "sim.user@example.com",
        },
        headers=auth_headers,
    )
    assert resp_failed.status_code == 200
    assert resp_failed.json()["status"] == "simulated"
    assert resp_failed.json()["event_type"] == "payment.failed"

    # 2. Simulate payment.captured
    resp_captured = client.post(
        "/api/v1/webhooks/simulate",
        json={
            "event_type": "payment.captured",
            "amount": 6200.0,
        },
        headers=auth_headers,
    )
    assert resp_captured.status_code == 200
    assert resp_captured.json()["event_type"] == "payment.captured"

    # 3. Simulate order.paid
    resp_order = client.post(
        "/api/v1/webhooks/simulate",
        json={
            "event_type": "order.paid",
            "amount": 3500.0,
        },
        headers=auth_headers,
    )
    assert resp_order.status_code == 200
    assert resp_order.json()["event_type"] == "order.paid"
