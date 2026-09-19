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

    # Safe migration for new columns in existing SQLite tables
    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            # Check bills_emis table columns
            res = conn.execute(text("PRAGMA table_info(bills_emis)")).fetchall()
            existing_cols = {row[1] for row in res}
            if existing_cols:
                if "risk_score" not in existing_cols:
                    conn.execute(text("ALTER TABLE bills_emis ADD COLUMN risk_score INTEGER DEFAULT 15"))
                if "risk_reason" not in existing_cols:
                    conn.execute(text("ALTER TABLE bills_emis ADD COLUMN risk_reason VARCHAR(255)"))
                if "risk_factors" not in existing_cols:
                    conn.execute(text("ALTER TABLE bills_emis ADD COLUMN risk_factors TEXT DEFAULT '[]'"))
                if "last_evaluated_at" not in existing_cols:
                    conn.execute(text("ALTER TABLE bills_emis ADD COLUMN last_evaluated_at DATETIME"))

            # Check bill_reminder_logs table columns
            log_res = conn.execute(text("PRAGMA table_info(bill_reminder_logs)")).fetchall()
            existing_log_cols = {row[1] for row in log_res}
            if existing_log_cols:
                if "stage" not in existing_log_cols:
                    conn.execute(text("ALTER TABLE bill_reminder_logs ADD COLUMN stage VARCHAR(40) DEFAULT 'normal'"))
                if "delivery_status" not in existing_log_cols:
                    conn.execute(text("ALTER TABLE bill_reminder_logs ADD COLUMN delivery_status VARCHAR(30) DEFAULT 'delivered'"))
                if "customer_response" not in existing_log_cols:
                    conn.execute(text("ALTER TABLE bill_reminder_logs ADD COLUMN customer_response VARCHAR(40) DEFAULT 'pending'"))
                if "payment_status_after" not in existing_log_cols:
                    conn.execute(text("ALTER TABLE bill_reminder_logs ADD COLUMN payment_status_after VARCHAR(30) DEFAULT 'pending'"))
            # Check recovery_cases table columns
            rc_res = conn.execute(text("PRAGMA table_info(recovery_cases)")).fetchall()
            existing_rc_cols = {row[1] for row in rc_res}
            if existing_rc_cols:
                if "stage" not in existing_rc_cols:
                    conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN stage VARCHAR(50) DEFAULT 'failed'"))
                if "whatsapp_status" not in existing_rc_cols:
                    conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN whatsapp_status VARCHAR(30) DEFAULT 'not_dispatched'"))
                if "customer_response" not in existing_rc_cols:
                    conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN customer_response VARCHAR(30) DEFAULT 'pending'"))
                if "payment_link_id" not in existing_rc_cols:
                    conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN payment_link_id VARCHAR(100)"))
                if "payment_link_url" not in existing_rc_cols:
                    conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN payment_link_url VARCHAR(500)"))
                if "verified_payment_id" not in existing_rc_cols:
                    conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN verified_payment_id VARCHAR(100)"))
    except Exception:
        pass


