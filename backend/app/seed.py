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
from app.models.bills import BillEmi, BillReminderLog, BillReminderSettings, BillRiskHistory
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

    # 5. Seed Bills & EMIs
    if db.query(BillEmi).filter_by(merchant_id=merchant.id).count() == 0:
        now = datetime.now(timezone.utc)
        custs = db.query(Customer).filter_by(merchant_id=merchant.id).all()
        
        sample_bills = [
            {
                "name": "Tata Power Commercial Electricity",
                "category": "Electricity",
                "amount": 18450.0,
                "due_date": now + timedelta(days=2),
                "recurrence": "Monthly",
                "customer_name": "Rajesh Sharma",
                "customer_phone": "9876543210",
                "customer_email": "rajesh.sharma@example.com",
                "payment_link": "https://pay.recoverai.dev/bill/elec-01",
                "notes": "Main server room & office floor electricity connection.",
                "status": "Upcoming",
                "risk_level": "Medium",
            },
            {
                "name": "Airtel Fiber Gigabit Leased Line",
                "category": "Internet",
                "amount": 6999.0,
                "due_date": now + timedelta(hours=6),
                "recurrence": "Monthly",
                "customer_name": "Priya Patel",
                "customer_phone": "9823456789",
                "customer_email": "priya.p@example.com",
                "payment_link": "https://pay.recoverai.dev/bill/net-01",
                "notes": "Primary office fiber line with 99.9% uptime SLA.",
                "status": "Due Today",
                "risk_level": "Medium",
            },
            {
                "name": "HDFC Commercial Property Loan EMI",
                "category": "EMI",
                "amount": 78500.0,
                "due_date": now - timedelta(days=4),
                "recurrence": "Monthly",
                "customer_name": "Vikas Malhotra",
                "customer_phone": "9811223344",
                "customer_email": "vikas.m@example.com",
                "payment_link": "https://pay.recoverai.dev/bill/hdfc-emi-01",
                "notes": "EMI Installment #34 of 120. Needs immediate settlement.",
                "status": "Overdue",
                "risk_level": "High",
            },
            {
                "name": "Jio Corporate Mobile CUG Fleet",
                "category": "Mobile",
                "amount": 4200.0,
                "due_date": now + timedelta(days=5),
                "recurrence": "Monthly",
                "customer_name": "Amit Deshmukh",
                "customer_phone": "9765432109",
                "customer_email": "amit.d@example.com",
                "payment_link": "https://pay.recoverai.dev/bill/jio-cug",
                "notes": "Corporate post-paid plan for field sales team (14 lines).",
                "status": "Upcoming",
                "risk_level": "Low",
            },
            {
                "name": "DLF CyberCity Office Rent (Block B)",
                "category": "Rent",
                "amount": 125000.0,
                "due_date": now + timedelta(days=12),
                "recurrence": "Monthly",
                "customer_name": "DLF Commercial Assets Ltd",
                "customer_phone": "9900112233",
                "customer_email": "accounts@dlfcyber.com",
                "payment_link": "https://pay.recoverai.dev/bill/dlf-rent",
                "notes": "Monthly lease for HQ premises 4th floor.",
                "status": "Upcoming",
                "risk_level": "Low",
            },
            {
                "name": "ICICI Lombard Group Health Insurance",
                "category": "Insurance",
                "amount": 46200.0,
                "due_date": now - timedelta(days=8),
                "recurrence": "Quarterly",
                "customer_name": "Sunita Rao",
                "customer_phone": "9833445566",
                "customer_email": "sunita.rao@example.com",
                "payment_link": "https://pay.recoverai.dev/bill/icici-ins",
                "notes": "Quarterly premium for 50 employee group medical cover.",
                "status": "Overdue",
                "risk_level": "High",
            },
            {
                "name": "AWS Cloud Infrastructure Billing",
                "category": "Subscription",
                "amount": 34800.0,
                "due_date": now + timedelta(days=4),
                "recurrence": "Monthly",
                "customer_name": "Karan Singhal",
                "customer_phone": "9845012345",
                "customer_email": "karan.s@example.com",
                "payment_link": "https://pay.recoverai.dev/bill/aws-cloud",
                "notes": "Production Kubernetes & RDS database clusters.",
                "status": "Upcoming",
                "risk_level": "Medium",
            },
            {
                "name": "Canon Industrial Printer Equipment EMI",
                "category": "EMI",
                "amount": 14500.0,
                "due_date": now - timedelta(days=15),
                "recurrence": "Monthly",
                "customer_name": "Kavita Nair",
                "customer_phone": "9877665544",
                "customer_email": "kavita.n@example.com",
                "payment_link": "https://pay.recoverai.dev/bill/canon-emi",
                "notes": "Lease finance installment #18 of 36.",
                "status": "Paid",
                "risk_level": "Low",
            },
            {
                "name": "HubSpot Marketing & CRM Suite",
                "category": "Subscription",
                "amount": 19500.0,
                "due_date": now + timedelta(days=18),
                "recurrence": "Monthly",
                "customer_name": "Rohan Gupta",
                "customer_phone": "9899887766",
                "customer_email": "rohan.g@example.com",
                "payment_link": "https://pay.recoverai.dev/bill/hubspot",
                "notes": "Enterprise tier annual commit billed monthly.",
                "status": "Upcoming",
                "risk_level": "Low",
            },
            {
                "name": "Water & Utility Municipal Tax",
                "category": "Other",
                "amount": 5400.0,
                "due_date": now + timedelta(days=1),
                "recurrence": "Quarterly",
                "customer_name": "Municipal Corporation",
                "customer_phone": "9811002299",
                "customer_email": "utilities@mc.gov.in",
                "payment_link": "https://pay.recoverai.dev/bill/muni-tax",
                "notes": "Commercial zone quarterly water cess.",
                "status": "Upcoming",
                "risk_level": "Medium",
            },
        ]

        for b_data in sample_bills:
            cust = custs[random.randint(0, len(custs) - 1)] if custs else None
            paid_time = now - timedelta(days=2) if b_data["status"] == "Paid" else None
            b_obj = BillEmi(
                merchant_id=merchant.id,
                customer_id=cust.id if cust else None,
                name=b_data["name"],
                category=b_data["category"],
                amount=b_data["amount"],
                currency="INR",
                due_date=b_data["due_date"],
                recurrence=b_data["recurrence"],
                customer_name=b_data["customer_name"],
                customer_phone=b_data["customer_phone"],
                customer_email=b_data["customer_email"],
                payment_link=b_data["payment_link"],
                notes=b_data["notes"],
                status=b_data["status"],
                paid_at=paid_time,
            )
            db.add(b_obj)
            db.commit()
            db.refresh(b_obj)

            # Evaluate with AI Risk Engine
            from app.services.bill_risk_engine import evaluate_bill
            evaluate_bill(db, b_obj, save_history=True)

            # Seed an earlier historical risk evaluation for trend demonstration
            hist_eval = BillRiskHistory(
                bill_id=b_obj.id,
                merchant_id=merchant.id,
                risk_score=max(10, b_obj.risk_score - 15),
                risk_level="Low" if b_obj.risk_score - 15 <= 30 else "Medium",
                risk_reason="Initial baseline risk assessment on bill creation",
                evaluated_at=_utc(days_ago=5),
            )
            hist_eval.set_factors(["Standard recurring cycle baseline", "Customer account active"])
            db.add(hist_eval)
            db.commit()

            # Seed realistic multi-stage reminder logs for demonstration
            if b_data["status"] == "Overdue":
                log1 = BillReminderLog(
                    bill_id=b_obj.id,
                    merchant_id=merchant.id,
                    stage="3-day",
                    channel="whatsapp",
                    recipient_phone=b_obj.customer_phone,
                    message=f"Hello {b_obj.customer_name}, your {b_obj.category} payment '{b_obj.name}' of ₹{b_obj.amount:,.0f} is due in 3 days. Link: {b_obj.payment_link}",
                    status="delivered",
                    delivery_status="delivered",
                    customer_response="opened_link",
                    payment_status_after="pending",
                    sent_at=_utc(days_ago=11, hours=2),
                )
                log2 = BillReminderLog(
                    bill_id=b_obj.id,
                    merchant_id=merchant.id,
                    stage="due_today",
                    channel="whatsapp",
                    recipient_phone=b_obj.customer_phone,
                    message=f"Payment Due Today: Hi {b_obj.customer_name}, ₹{b_obj.amount:,.0f} for {b_obj.name} is due today. Pay securely: {b_obj.payment_link}",
                    status="delivered",
                    delivery_status="delivered",
                    customer_response="responded",
                    payment_status_after="pending",
                    sent_at=_utc(days_ago=8, hours=4),
                )
                log3 = BillReminderLog(
                    bill_id=b_obj.id,
                    merchant_id=merchant.id,
                    stage="overdue",
                    channel="sms",
                    recipient_phone=b_obj.customer_phone,
                    message=f"Action Required: {b_obj.customer_name}, your {b_obj.name} payment of ₹{b_obj.amount:,.0f} is overdue. Pay immediately: {b_obj.payment_link}",
                    status="delivered",
                    delivery_status="delivered",
                    customer_response="pending",
                    payment_status_after="pending",
                    sent_at=_utc(days_ago=3, hours=1),
                )
                db.add_all([log1, log2, log3])
                db.commit()

            elif b_data["status"] == "Due Today":
                log = BillReminderLog(
                    bill_id=b_obj.id,
                    merchant_id=merchant.id,
                    stage="due_today",
                    channel="whatsapp",
                    recipient_phone=b_obj.customer_phone,
                    message=f"Payment Due Today: Hi {b_obj.customer_name}, your {b_obj.category} payment '{b_obj.name}' of ₹{b_obj.amount:,.0f} is due today. Pay at: {b_obj.payment_link}",
                    status="delivered",
                    delivery_status="delivered",
                    customer_response="pending",
                    payment_status_after="pending",
                    sent_at=_utc(days_ago=0, hours=2),
                )
                db.add(log)
                db.commit()

            elif b_data["status"] == "Paid":
                log = BillReminderLog(
                    bill_id=b_obj.id,
                    merchant_id=merchant.id,
                    stage="1-day",
                    channel="whatsapp",
                    recipient_phone=b_obj.customer_phone,
                    message=f"Important Reminder: {b_obj.customer_name}, {b_obj.name} payment of ₹{b_obj.amount:,.0f} is due tomorrow. Link: {b_obj.payment_link}",
                    status="delivered",
                    delivery_status="delivered",
                    customer_response="paid",
                    payment_status_after="settled",
                    sent_at=_utc(days_ago=16, hours=5),
                )
                db.add(log)
                db.commit()

        # Seed BillReminderSettings
        if db.query(BillReminderSettings).filter_by(merchant_id=merchant.id).count() == 0:
            settings = BillReminderSettings(
                merchant_id=merchant.id,
                reminders_enabled=True,
                frequency="smart",
                max_reminders=4,
                preferred_channel="whatsapp",
                quiet_hours_enabled=True,
                quiet_hours_start="22:00",
                quiet_hours_end="08:00",
                risk_multiplier_enabled=True,
            )
            db.add(settings)
            db.commit()


    # 6. Orders & Subscriptions
    if db.query(Order).filter_by(merchant_id=merchant.id).count() == 0:
        customers = db.query(Customer).filter_by(merchant_id=merchant.id).all()
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
