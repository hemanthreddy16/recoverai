"""Tests for Smart Payment Reminder Engine."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.main import app
from app.models.bills import BillEmi, BillReminderLog, BillReminderSettings
from app.models.users import Merchant
from app.services.smart_reminder_engine import (
    SmartReminderEngine,
    WhatsAppProvider,
    EmailProvider,
    SMSProvider,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_context(client: TestClient):
    email = f"reminder_admin_{id(client)}@test.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "merchant_name": "Smart Reminders Merchant",
            "full_name": "Reminder Admin",
            "role": "admin",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "merchant_id": resp.json()["user"]["merchant_id"],
    }


@pytest.fixture
def db_session():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_channel_providers_sandbox():
    """Verify mock channel providers simulate message transmission safely."""
    res_wa = WhatsAppProvider.send_template("9876543210", "Electricity Bill", 1500.0, "2026-10-01", "https://pay.link")
    assert res_wa["status"] == "delivered"
    assert res_wa["delivery_status"] == "delivered"

    res_em = EmailProvider.send_email("user@test.com", "SaaS Sub", 999.0, "2026-10-01", None)
    assert res_em["status"] == "delivered"

    res_sms = SMSProvider.send_sms("9876543210", "Car EMI", 12000.0, "2026-10-01", None)
    assert res_sms["status"] == "delivered"


def test_quiet_hours_evaluation(db_session: Session, auth_context: dict):
    """Verify quiet hours handling including overnight window wrapping."""
    merchant_id = auth_context["merchant_id"]
    settings = SmartReminderEngine.get_or_create_settings(db_session, merchant_id)
    settings.quiet_hours_enabled = True
    settings.quiet_hours_start = "22:00"
    settings.quiet_hours_end = "08:00"
    db_session.commit()

    # 23:30 is in quiet hours
    dt_night = datetime(2026, 9, 20, 23, 30, 0, tzinfo=timezone.utc)
    assert SmartReminderEngine.is_in_quiet_hours(settings, dt_night) is True

    # 04:00 is in quiet hours
    dt_early = datetime(2026, 9, 20, 4, 0, 0, tzinfo=timezone.utc)
    assert SmartReminderEngine.is_in_quiet_hours(settings, dt_early) is True

    # 14:00 is outside quiet hours
    dt_day = datetime(2026, 9, 20, 14, 0, 0, tzinfo=timezone.utc)
    assert SmartReminderEngine.is_in_quiet_hours(settings, dt_day) is False


def test_anti_spam_cooldown_and_max_reminders(db_session: Session, auth_context: dict):
    """Verify anti-spam prevents excessive or repeated reminders."""
    merchant_id = auth_context["merchant_id"]
    settings = SmartReminderEngine.get_or_create_settings(db_session, merchant_id)
    settings.max_reminders = 2
    settings.frequency = "smart"
    db_session.commit()

    now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)

    bill = BillEmi(
        merchant_id=merchant_id,
        name="Broadband Fiber",
        category="Internet",
        amount=1200.0,
        currency="INR",
        due_date=now + timedelta(days=3),
        recurrence="Monthly",
        customer_name="Aarav Sharma",
        customer_phone="9876500001",
        status="Upcoming",
        risk_score=20,
        risk_level="Low",
    )
    db_session.add(bill)
    db_session.commit()

    # First evaluation -> should schedule 3-day reminder
    candidate1 = SmartReminderEngine.evaluate_bill_schedule(bill, settings, db_session, now)
    assert candidate1 is not None
    assert candidate1.stage == "3-day"

    # Record that 3-day was just sent 2 hours ago
    log1 = BillReminderLog(
        bill_id=bill.id,
        merchant_id=merchant_id,
        stage="3-day",
        channel="whatsapp",
        recipient_phone=bill.customer_phone,
        message="Test reminder",
        status="delivered",
        delivery_status="delivered",
        sent_at=now - timedelta(hours=2),
    )
    db_session.add(log1)
    db_session.commit()

    # Re-evaluate -> should be None (already sent 3-day and within cooldown)
    candidate2 = SmartReminderEngine.evaluate_bill_schedule(bill, settings, db_session, now)
    assert candidate2 is None

    # If max_reminders reached
    log2 = BillReminderLog(
        bill_id=bill.id,
        merchant_id=merchant_id,
        stage="1-day",
        channel="whatsapp",
        recipient_phone=bill.customer_phone,
        message="Test 2",
        status="delivered",
        delivery_status="delivered",
        sent_at=now - timedelta(days=2),
    )
    db_session.add(log2)
    db_session.commit()

    candidate3 = SmartReminderEngine.evaluate_bill_schedule(bill, settings, db_session, now)
    assert candidate3 is None  # max_reminders (2) reached


def test_ai_risk_modulated_scheduling(db_session: Session, auth_context: dict):
    """Verify high risk bills trigger recovery and advance reminders."""
    merchant_id = auth_context["merchant_id"]
    settings = SmartReminderEngine.get_or_create_settings(db_session, merchant_id)
    settings.max_reminders = 5
    settings.risk_multiplier_enabled = True
    db_session.commit()

    now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)

    # 7-day bill with high risk (score 75)
    bill_high_risk = BillEmi(
        merchant_id=merchant_id,
        name="Machinery Lease EMI",
        category="EMI",
        amount=85000.0,
        currency="INR",
        due_date=now + timedelta(days=6),
        recurrence="Monthly",
        customer_name="High Risk Customer",
        customer_phone="9876500002",
        status="Upcoming",
        risk_score=75,
        risk_level="High",
    )
    db_session.add(bill_high_risk)
    db_session.commit()

    candidate = SmartReminderEngine.evaluate_bill_schedule(bill_high_risk, settings, db_session, now)
    assert candidate is not None
    assert candidate.stage == "7-day"
    assert "High" in candidate.reason or "75" in candidate.reason


def test_reminder_settings_endpoints(client: TestClient, auth_context: dict):
    """Test GET and PUT /bills/reminders/settings."""
    headers = auth_context["headers"]

    # GET settings
    res = client.get("/api/v1/bills/reminders/settings", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "reminders_enabled" in data
    assert "frequency" in data
    assert "quiet_hours_start" in data

    # PUT settings
    payload = {
        "reminders_enabled": True,
        "frequency": "aggressive",
        "max_reminders": 6,
        "preferred_channel": "email",
        "quiet_hours_enabled": True,
        "quiet_hours_start": "23:00",
        "quiet_hours_end": "07:00",
        "risk_multiplier_enabled": True,
    }
    update_res = client.put("/api/v1/bills/reminders/settings", json=payload, headers=headers)
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["frequency"] == "aggressive"
    assert updated["max_reminders"] == 6
    assert updated["preferred_channel"] == "email"
    assert updated["quiet_hours_start"] == "23:00"


def test_upcoming_actions_and_dispatch_endpoints(client: TestClient, auth_context: dict):
    """Test GET /bills/reminders/upcoming-actions and POST /bills/reminders/evaluate-and-dispatch."""
    headers = auth_context["headers"]

    # Ensure settings allow dispatch outside quiet hours for test
    client.put("/api/v1/bills/reminders/settings", json={"quiet_hours_enabled": False, "reminders_enabled": True}, headers=headers)

    # 1. Upcoming actions
    res = client.get("/api/v1/bills/reminders/upcoming-actions", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "scheduled_count" in data
    assert "sent_count" in data
    assert "recovered_count" in data
    assert "queue" in data
    assert isinstance(data["queue"], list)

    # 2. Evaluate and dispatch
    dispatch_res = client.post("/api/v1/bills/reminders/evaluate-and-dispatch", headers=headers)
    assert dispatch_res.status_code == 200
    d_data = dispatch_res.json()
    assert "dispatched_count" in d_data
    assert "dispatched_logs" in d_data


def test_reminder_timeline_endpoint(client: TestClient, auth_context: dict, db_session: Session):
    """Test GET /bills/{bill_id}/timeline."""
    headers = auth_context["headers"]
    merchant_id = auth_context["merchant_id"]
    
    bill = db_session.query(BillEmi).filter_by(merchant_id=merchant_id).first()
    assert bill is not None

    res = client.get(f"/api/v1/bills/{bill.id}/timeline", headers=headers)
    assert res.status_code == 200
    timeline = res.json()
    assert isinstance(timeline, list)
    assert len(timeline) >= 2  # At least creation + risk assessment
    
    stages = [step["stage"] for step in timeline]
    assert "creation" in stages
    assert "risk_assessment" in stages
