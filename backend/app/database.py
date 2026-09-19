"""SQLAlchemy engine, session factory and declarative base.

The database backend is configurable through DATABASE_URL so the project runs
against SQLite locally and PostgreSQL inside Docker without code changes.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    connect_args = {}
    # SQLite needs check_same_thread=False for use across FastAPI threads.
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True, pool_recycle=300)



engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    # Import models so they are registered on Base before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Safe migration for new columns in existing SQLite/Postgres tables
    try:
        from sqlalchemy import inspect, text
        insp = inspect(engine)
        tables = insp.get_table_names()

        with engine.begin() as conn:
            # Check recovery_cases table columns
            if "recovery_cases" in tables:
                cols = {c["name"] for c in insp.get_columns("recovery_cases")}
                if "stage" not in cols:
                    conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN stage VARCHAR(50) DEFAULT 'failed'"))
                if "whatsapp_status" not in cols:
                    conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN whatsapp_status VARCHAR(30) DEFAULT 'not_dispatched'"))
                if "customer_response" not in cols:
                    conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN customer_response VARCHAR(30) DEFAULT 'pending'"))
                if "payment_link_id" not in cols:
                    conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN payment_link_id VARCHAR(100)"))
                if "payment_link_url" not in cols:
                    conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN payment_link_url VARCHAR(500)"))
                if "verified_payment_id" not in cols:
                    conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN verified_payment_id VARCHAR(100)"))

            # Check bills_emis table columns
            if "bills_emis" in tables:
                cols = {c["name"] for c in insp.get_columns("bills_emis")}
                if "risk_score" not in cols:
                    conn.execute(text("ALTER TABLE bills_emis ADD COLUMN risk_score INTEGER DEFAULT 15"))
                if "risk_reason" not in cols:
                    conn.execute(text("ALTER TABLE bills_emis ADD COLUMN risk_reason VARCHAR(255)"))
                if "risk_factors" not in cols:
                    conn.execute(text("ALTER TABLE bills_emis ADD COLUMN risk_factors TEXT DEFAULT '[]'"))
                if "last_evaluated_at" not in cols:
                    conn.execute(text("ALTER TABLE bills_emis ADD COLUMN last_evaluated_at TIMESTAMP"))

            # Check bill_reminder_logs table columns
            if "bill_reminder_logs" in tables:
                cols = {c["name"] for c in insp.get_columns("bill_reminder_logs")}
                if "stage" not in cols:
                    conn.execute(text("ALTER TABLE bill_reminder_logs ADD COLUMN stage VARCHAR(40) DEFAULT 'normal'"))
                if "delivery_status" not in cols:
                    conn.execute(text("ALTER TABLE bill_reminder_logs ADD COLUMN delivery_status VARCHAR(30) DEFAULT 'delivered'"))
                if "customer_response" not in cols:
                    conn.execute(text("ALTER TABLE bill_reminder_logs ADD COLUMN customer_response VARCHAR(40) DEFAULT 'pending'"))
                if "payment_status_after" not in cols:
                    conn.execute(text("ALTER TABLE bill_reminder_logs ADD COLUMN payment_status_after VARCHAR(30) DEFAULT 'pending'"))
    except Exception:
        pass


