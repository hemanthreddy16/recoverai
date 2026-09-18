"""Database seeding: merchant, demo user, policy, and realistic demo data.

Run with:  python -m app.seed
Creates a login you can use in the UI:
    email:    demo@recoverai.dev
    password: recoverai123
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, create_all
from app.models.payments import Order, Payment, RevenueEvent, Subscription
from app.models.users import Customer, Merchant, User
from app.models.recovery import (
    AuditLog,
    MerchantPolicy,
    ModelPrediction,
    Notification,
    RecoveryAction,
    RecoveryCase,
)
from app.security import hash_password
from app.services.ml_pipeline import ensure_model, model_store

# Deterministic seeding for reproducible demos.
random.seed(7)

DEMO_EMAIL = "demo@recoverai.dev"
DEMO_PASSWORD = "recoverai123"


def _utc(days_ago: int = 0, hours: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours)


def seed(db: Session) -> None:
    create_all()
    ensure_model()

    # 1. Merchant
    merchant = db.query(Merchant).filter_by(slug="acme-commerce").first()
    if merchant is None:
        merchant = Merchant(name="Acme Commerce", slug="acme-commerce")
        db.add(merchant)
        db.commit()
        db.refresh(merchant)

    # 2. Demo User
    user = db.query(User).filter_by(email=DEMO_EMAIL).first()
    if user is None:
        user = User(
            merchant_id=merchant.id,
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Demo Operator",
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()

    # 3. Merchant Policy
    policy = db.query(MerchantPolicy).filter_by(merchant_id=merchant.id).first()
    if policy is None:
        policy = MerchantPolicy(
            merchant_id=merchant.id,
            automatic_threshold=0.55,
            approval_threshold=0.40,
            retry_limit=2,
            max_recovery_attempts=3,
            high_value_threshold=50000.0,
            allow_auto_retry=True,
            allow_auto_payment_link=False,
            allow_auto_notification=True,
            notification_channels=json.dumps(["email", "sms"]),
        )
        db.add(policy)
        db.commit()

    # 4. Customers
    if db.query(Customer).filter_by(merchant_id=merchant.id).count() == 0:
        customers = []
        for i in range(60):
            c = Customer(
                merchant_id=merchant.id,
                external_id=f"CUST-{1000 + i}",
                name=f"Customer {i}",
                email=f"customer{i}@example.com",
                phone=f"9999999{i:03d}"[:10],
                clv=round(random.uniform(1500, 75000), 2),
            )
            customers.append(c)
            db.add(c)
        db.commit()

        # 5. Orders & Subscriptions
        for idx, c in enumerate(customers[:25]):
            o = Order(
                merchant_id=merchant.id,
                customer_id=c.id,
                amount=round(random.uniform(500, 15000), 2),
                currency="INR",
                status="abandoned" if idx % 3 == 0 else "paid",
                abandoned_at=_utc(days_ago=random.randint(1, 15)) if idx % 3 == 0 else None,
                created_at=_utc(days_ago=random.randint(2, 30)),
            )
            db.add(o)

            sub = Subscription(
                merchant_id=merchant.id,
                customer_id=c.id,
                plan=random.choice(["starter", "growth", "pro", "enterprise"]),
                amount=round(random.uniform(999, 9999), 2),
                currency="INR",
                status="past_due" if idx % 4 == 0 else "active",
                failure_count=1 if idx % 4 == 0 else 0,
                created_at=_utc(days_ago=random.randint(10, 180)),
                current_period_end=_utc(days_ago=-random.randint(5, 30)),
            )
            db.add(sub)
        db.commit()

        # 6. Payments History
        reasons = [
            "insufficient_funds",
            "network_error",
            "card_declined",
            "expired_card",
            "payment_cancelled",
            "fraud_blocked",
            "subscription_hard_fail",
        ]
        for c in customers:
            n_hist = random.randint(3, 12)
            for _ in range(n_hist):
                ok = random.random() < 0.75
                p = Payment(
                    merchant_id=merchant.id,
                    customer_id=c.id,
                    amount=round(random.uniform(200, 20000), 2),
                    currency="INR",
                    status="captured" if ok else "failed",
                    failure_reason=None if ok else random.choice(reasons),
                    payment_method=random.choice(["card", "upi", "netbanking", "wallet"]),
                    created_at=_utc(days_ago=random.randint(1, 120)),
                )
                db.add(p)
        db.commit()

        # 7. Raw Revenue Events (Webhook Intake)
        for i in range(20):
            ev = RevenueEvent(
                merchant_id=merchant.id,
                event_type=random.choice(["payment.failed", "payment.authorized", "order.paid", "subscription.charged"]),
                amount=round(random.uniform(500, 12000), 2),
                currency="INR",
                status="processed",
                razorpay_event_id=f"event_sim_{i:04d}_{random.randint(1000, 9999)}",
                payload=json.dumps({"simulated": True, "event_idx": i, "timestamp": _utc(days_ago=i).isoformat()}),
                created_at=_utc(days_ago=i),
            )
            db.add(ev)
        db.commit()

        # 8. Audit Logs
        db.add(
            AuditLog(
                merchant_id=merchant.id,
                actor="system",
                action="system.seed",
                entity_type="merchant",
                entity_id=merchant.id,
                detail=json.dumps({"message": "Initial merchant environment and policy seeded"}),
                created_at=_utc(days_ago=1),
            )
        )
        db.commit()

    # 9. Seed recovery cases from a batch of fresh failures
    existing_cases = db.query(RecoveryCase).filter_by(merchant_id=merchant.id).count()
    if existing_cases == 0:
        from app.agents.detection import DetectionAgent
        from app.agents.base import AgentContext
        from app.mcp.gateway import MCPGateway
        from app.services.llm import get_llm
        from app.agents.orchestrator import process_case

        customers = db.query(Customer).filter_by(merchant_id=merchant.id).all()
        gateway = MCPGateway(db, merchant.id, caller="seed")
        ctx = AgentContext(db, merchant.id, get_llm(), gateway)

        scenarios = [
            ("insufficient_funds", 4500, "success"),
            ("network_error", 1200, "success"),
            ("card_declined", 8000, "success"),
            ("expired_card", 3200, "failure"),
            ("fraud_blocked", 60000, "failure"),
            ("payment_cancelled", 1500, "success"),
            ("subscription_hard_fail", 2200, "failure"),
            ("insufficient_funds", 90000, "success"),  # high value -> approval path
        ]
        for reason, amount, outcome in scenarios * 6:  # ~48 cases
            c = random.choice(customers)
            p = Payment(
                merchant_id=merchant.id,
                customer_id=c.id,
                amount=amount,
                currency="INR",
                status="failed",
                failure_reason=reason,
                payment_method=random.choice(["card", "upi", "netbanking"]),
                created_at=_utc(days_ago=random.randint(0, 10)),
            )
            db.add(p)
            db.commit()
            db.refresh(p)
            case = DetectionAgent(ctx).detect_failed_payment(p, reason=reason)
            # High-value -> simulate human approval in demo seed.
            auto_approve = amount >= 50000
            process_case(db, case, simulated_outcome=outcome, auto_approve=auto_approve)

    print("Seed complete.")
    print(f"  Merchant:      {merchant.name} (id={merchant.id})")
    print(f"  Login:         {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print(f"  Model:         {model_store.version}")
    print(f"  Customers:     {db.query(Customer).filter_by(merchant_id=merchant.id).count()}")
    print(f"  Payments:      {db.query(Payment).filter_by(merchant_id=merchant.id).count()}")
    print(f"  Orders:        {db.query(Order).filter_by(merchant_id=merchant.id).count()}")
    print(f"  Subscriptions: {db.query(Subscription).filter_by(merchant_id=merchant.id).count()}")
    print(f"  Cases:         {db.query(RecoveryCase).filter_by(merchant_id=merchant.id).count()}")
    print(f"  Revenue Events:{db.query(RevenueEvent).filter_by(merchant_id=merchant.id).count()}")


def main() -> None:
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
