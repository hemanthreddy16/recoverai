"""Database, ORM model, and migration tests."""
from __future__ import annotations

import json
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    AgentDecision,
    AgentRun,
    AuditLog,
    Customer,
    MCPToolCall,
    Merchant,
    MerchantPolicy,
    ModelPrediction,
    Notification,
    Order,
    Payment,
    RecoveryAction,
    RecoveryCase,
    RevenueEvent,
    Subscription,
    User,
)
from app.seed import seed


@pytest.fixture(scope="module")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


def test_merchant_and_user_creation(db_session):
    merchant = Merchant(name="Test Merchant", slug="test-merchant")
    db_session.add(merchant)
    db_session.commit()
    db_session.refresh(merchant)
    assert merchant.id is not None

    user = User(
        merchant_id=merchant.id,
        email="test_user@example.com",
        hashed_password="hashed_pw_test",
        full_name="Test Operator",
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    assert user.id is not None
    assert user.merchant_id == merchant.id


def test_customer_order_subscription_payment(db_session):
    merchant = db_session.query(Merchant).first()
    assert merchant is not None

    customer = Customer(
        merchant_id=merchant.id,
        external_id="CUST-TEST-001",
        name="Alice Tester",
        email="alice@test.com",
        phone="9876543210",
        clv=12500.0,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    assert customer.id is not None

    order = Order(
        merchant_id=merchant.id,
        customer_id=customer.id,
        amount=3400.0,
        currency="INR",
        status="abandoned",
        abandoned_at=datetime.now(timezone.utc),
    )
    db_session.add(order)

    subscription = Subscription(
        merchant_id=merchant.id,
        customer_id=customer.id,
        plan="growth",
        amount=4999.0,
        status="past_due",
        failure_count=1,
    )
    db_session.add(subscription)

    payment = Payment(
        merchant_id=merchant.id,
        customer_id=customer.id,
        amount=3400.0,
        currency="INR",
        status="failed",
        failure_reason="insufficient_funds",
        payment_method="card",
    )
    db_session.add(payment)
    db_session.commit()

    assert order.id is not None
    assert subscription.id is not None
    assert payment.id is not None


def test_recovery_case_and_actions(db_session):
    merchant = db_session.query(Merchant).first()
    customer = db_session.query(Customer).first()
    payment = db_session.query(Payment).first()

    case = RecoveryCase(
        merchant_id=merchant.id,
        customer_id=customer.id,
        payment_id=payment.id,
        amount_at_risk=3400.0,
        risk_score=0.35,
        event_type="failed_payment",
        failure_reason="insufficient_funds",
        recovery_probability=0.82,
        recommended_action="create_payment_link",
        policy_decision="approval",
        recovery_status="open",
    )
    case.set_contributing_factors(["Insufficient account balance", "Card active"])
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    assert case.id is not None
    assert "Insufficient account balance" in case.get_contributing_factors()

    action = RecoveryAction(
        merchant_id=merchant.id,
        case_id=case.id,
        action_type="create_payment_link",
        channel="email",
        status="executed",
    )
    action.set_detail({"link": "https://rzp.io/i/test1234"})
    db_session.add(action)
    db_session.commit()
    assert action.id is not None
    assert action.get_detail()["link"] == "https://rzp.io/i/test1234"


def test_agent_runs_decisions_and_mcp_calls(db_session):
    merchant = db_session.query(Merchant).first()
    case = db_session.query(RecoveryCase).first()

    run = AgentRun(
        merchant_id=merchant.id,
        case_id=case.id,
        agent_name="prediction",
        status="finished",
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    decision = AgentDecision(
        agent_run_id=run.id,
        case_id=case.id,
        merchant_id=merchant.id,
        agent_name="prediction",
        decision_type="recovery_probability",
        confidence=0.85,
    )
    decision.set_input({"amount": 3400})
    decision.set_output({"probability": 0.82})
    db_session.add(decision)

    tool_call = MCPToolCall(
        merchant_id=merchant.id,
        case_id=case.id,
        tool_name="create_payment_link",
        status="ok",
        duration_ms=45,
    )
    tool_call.set_arguments({"amount": 3400})
    tool_call.set_result({"payment_link_id": "plink_test"})
    db_session.add(tool_call)

    db_session.commit()
    assert run.id is not None
    assert decision.id is not None
    assert tool_call.id is not None


def test_audit_logs_predictions_policy_and_notifications(db_session):
    merchant = db_session.query(Merchant).first()
    case = db_session.query(RecoveryCase).first()

    log = AuditLog(
        merchant_id=merchant.id,
        actor="operator_1",
        action="case.approved",
        entity_type="recovery_case",
        entity_id=case.id,
    )
    log.set_detail({"note": "Approved manual retry"})
    db_session.add(log)

    pred = ModelPrediction(
        merchant_id=merchant.id,
        case_id=case.id,
        model_version="gb_v1.0",
        recovery_probability=0.82,
        predicted_label=1,
    )
    db_session.add(pred)

    notif = Notification(
        merchant_id=merchant.id,
        case_id=case.id,
        channel="email",
        subject="Payment Retry Notice",
        body="Your payment link is ready.",
        status="sent",
    )
    db_session.add(notif)

    policy = MerchantPolicy(
        merchant_id=merchant.id,
        automatic_threshold=0.6,
        approval_threshold=0.35,
        high_value_threshold=40000.0,
    )
    policy.set_channels(["email", "sms", "whatsapp"])
    db_session.add(policy)

    rev_ev = RevenueEvent(
        merchant_id=merchant.id,
        event_type="payment.failed",
        amount=3400.0,
        razorpay_event_id="ev_test_12345",
    )
    db_session.add(rev_ev)

    db_session.commit()
    assert log.id is not None
    assert pred.id is not None
    assert notif.id is not None
    assert policy.id is not None
    assert "whatsapp" in policy.get_channels()
    assert rev_ev.id is not None


def test_seed_execution(db_session):
    # Test that full seed pipeline completes without exception
    seed(db_session)
    assert db_session.query(Merchant).filter_by(slug="acme-commerce").count() >= 1
    assert db_session.query(Customer).count() >= 50
    assert db_session.query(RecoveryCase).count() >= 10


def test_alembic_migration_fresh_db(tmp_path):
    from alembic.config import Config
    from alembic import command

    db_file = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_file}"

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")

    eng = create_engine(db_url)
    with eng.connect() as conn:
        tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
        table_names = {t[0] for t in tables}
        expected = {
            "merchants",
            "users",
            "customers",
            "orders",
            "subscriptions",
            "payments",
            "revenue_events",
            "recovery_cases",
            "recovery_actions",
            "agent_runs",
            "agent_decisions",
            "mcp_tool_calls",
            "notifications",
            "audit_logs",
            "model_predictions",
            "merchant_policies",
        }
        for tbl in expected:
            assert tbl in table_names, f"Missing table {tbl}"
