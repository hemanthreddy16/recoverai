"""Tests for Bills & EMIs module: CRUD, summary metrics, filters, WhatsApp reminders, and tenant scoping."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_context(client: TestClient):
    email = f"bills_admin_{id(client)}@test.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "merchant_name": "Bills Test Corp",
            "full_name": "Bills Admin",
            "role": "admin",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "merchant_id": resp.json()["user"]["merchant_id"],
    }


def test_create_and_list_bills(client: TestClient, auth_context: dict):
    headers = auth_context["headers"]
    now = datetime.now(timezone.utc)
    
    # 1. Create upcoming electricity bill
    due_upcoming = (now + timedelta(days=5)).isoformat()
    resp = client.post(
        "/api/v1/bills",
        headers=headers,
        json={
            "name": "BSES Yamuna Electricity",
            "category": "Electricity",
            "amount": 12500.0,
            "due_date": due_upcoming,
            "recurrence": "Monthly",
            "customer_name": "Anil Kapoor",
            "customer_phone": "9811122233",
            "customer_email": "anil@example.com",
            "payment_link": "https://pay.example.com/elec1",
            "notes": "Plant utility connection",
        },
    )
    assert resp.status_code == 201, resp.text
    b1 = resp.json()
    assert b1["name"] == "BSES Yamuna Electricity"
    assert b1["status"] == "Upcoming"
    assert b1["days_remaining"] >= 4
    assert b1["days_overdue"] == 0

    # 2. Create overdue EMI
    due_overdue = (now - timedelta(days=6)).isoformat()
    resp2 = client.post(
        "/api/v1/bills",
        headers=headers,
        json={
            "name": "Axis Business Loan EMI",
            "category": "EMI",
            "amount": 45000.0,
            "due_date": due_overdue,
            "recurrence": "Monthly",
            "customer_name": "Deepak Mehta",
            "customer_phone": "9822233344",
            "customer_email": "deepak@example.com",
            "payment_link": "https://pay.example.com/emi1",
            "notes": "Machinery loan EMI",
        },
    )
    assert resp2.status_code == 201, resp2.text
    b2 = resp2.json()
    assert b2["status"] == "Overdue"
    assert b2["risk_level"] == "High"
    assert b2["days_overdue"] >= 5

    # 3. List bills
    list_resp = client.get("/api/v1/bills", headers=headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 2

    # 4. Filter by category
    elec_resp = client.get("/api/v1/bills?category=Electricity", headers=headers)
    assert elec_resp.status_code == 200
    elec_items = elec_resp.json()
    assert any(b["name"] == "BSES Yamuna Electricity" for b in elec_items)
    assert all(b["category"] == "Electricity" for b in elec_items)

    # 5. Search
    search_resp = client.get("/api/v1/bills?search=Anil", headers=headers)
    assert search_resp.status_code == 200
    s_items = search_resp.json()
    assert len(s_items) >= 1
    assert s_items[0]["customer_name"] == "Anil Kapoor"


def test_bill_summary_metrics(client: TestClient, auth_context: dict):
    headers = auth_context["headers"]
    resp = client.get("/api/v1/bills/summary", headers=headers)
    assert resp.status_code == 200
    s = resp.json()
    assert "total_upcoming_count" in s
    assert "total_amount_due" in s
    assert "overdue_count" in s
    assert "overdue_amount" in s
    assert "upcoming_vs_overdue" in s
    assert "category_breakdown" in s
    assert "monthly_trend" in s
    assert s["overdue_count"] >= 1


def test_mark_bill_paid_and_update(client: TestClient, auth_context: dict):
    headers = auth_context["headers"]
    now = datetime.now(timezone.utc)
    
    # Create bill
    resp = client.post(
        "/api/v1/bills",
        headers=headers,
        json={
            "name": "Spectranet Fiber Internet",
            "category": "Internet",
            "amount": 3500.0,
            "due_date": now.isoformat(),
            "recurrence": "Monthly",
            "customer_name": "Ravi Shastri",
            "customer_phone": "9833344455",
        },
    )
    assert resp.status_code == 201
    bill_id = resp.json()["id"]

    # Update bill notes and amount
    patch_resp = client.patch(
        f"/api/v1/bills/{bill_id}",
        headers=headers,
        json={"notes": "Upgraded plan to 500Mbps", "amount": 4200.0},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["amount"] == 4200.0
    assert patch_resp.json()["notes"] == "Upgraded plan to 500Mbps"

    # Mark as paid
    paid_resp = client.post(f"/api/v1/bills/{bill_id}/mark-paid", headers=headers)
    assert paid_resp.status_code == 200
    assert paid_resp.json()["status"] == "Paid"
    assert paid_resp.json()["paid_at"] is not None


def test_send_whatsapp_reminder(client: TestClient, auth_context: dict):
    headers = auth_context["headers"]
    now = datetime.now(timezone.utc)
    
    # Create bill
    resp = client.post(
        "/api/v1/bills",
        headers=headers,
        json={
            "name": "Tata Sky DTH Office Lounge",
            "category": "Subscription",
            "amount": 1200.0,
            "due_date": (now + timedelta(days=1)).isoformat(),
            "recurrence": "Monthly",
            "customer_name": "Mohit Sehgal",
            "customer_phone": "9844455566",
            "payment_link": "https://pay.example.com/dth",
        },
    )
    assert resp.status_code == 201
    bill_id = resp.json()["id"]

    # Send WhatsApp reminder
    wa_resp = client.post(
        f"/api/v1/bills/{bill_id}/send-whatsapp",
        headers=headers,
        json={"include_payment_link": True},
    )
    assert wa_resp.status_code == 200
    wa_data = wa_resp.json()
    assert wa_data["status"] == "success"
    assert "https://wa.me/" in wa_data["whatsapp_direct_url"]
    assert "Mohit" in wa_data["rendered_message"]

    # Check that bill detail includes the reminder log
    get_resp = client.get(f"/api/v1/bills/{bill_id}", headers=headers)
    assert get_resp.status_code == 200
    assert len(get_resp.json()["reminder_logs"]) >= 1
    assert get_resp.json()["reminder_logs"][0]["channel"] == "whatsapp"


def test_delete_bill(client: TestClient, auth_context: dict):
    headers = auth_context["headers"]
    now = datetime.now(timezone.utc)
    
    resp = client.post(
        "/api/v1/bills",
        headers=headers,
        json={
            "name": "Temporary Test Bill",
            "category": "Other",
            "amount": 500.0,
            "due_date": now.isoformat(),
            "customer_name": "Test User",
            "customer_phone": "9855566677",
        },
    )
    bill_id = resp.json()["id"]

    del_resp = client.delete(f"/api/v1/bills/{bill_id}", headers=headers)
    assert del_resp.status_code == 204

    # Confirm 404
    get_resp = client.get(f"/api/v1/bills/{bill_id}", headers=headers)
    assert get_resp.status_code == 404
