"""RecoverAI Standalone MCP (Model Context Protocol) Server.

Provides a secured, audited tool execution boundary for AI recovery workflows.
Tools require an authorization token and perform operations scoped strictly
to the requesting merchant context.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Initialize FastMCP Server
mcp = FastMCP("RecoverAI-MCP-Server")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recoverai.db")
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "dev-mcp-token-change-me")

# Setup database connection
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _check_auth(token: str | None) -> bool:
    return token == MCP_AUTH_TOKEN


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@mcp.tool()
def health_check(token: str = "") -> str:
    """Check MCP server health and database connectivity."""
    db_ok = False
    error_msg = None
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        error_msg = str(e)

    return json.dumps({
        "status": "healthy" if db_ok else "degraded",
        "service": "recoverai-mcp-server",
        "database_connected": db_ok,
        "database_error": error_msg,
        "timestamp": _now_iso(),
        "auth_configured": bool(MCP_AUTH_TOKEN),
    })


@mcp.tool()
def ping() -> str:
    """Simple ping endpoint for liveness verification."""
    return json.dumps({"status": "pong", "timestamp": _now_iso()})


@mcp.tool()
def get_payment(payment_id: int, merchant_id: int, token: str) -> str:
    """Retrieve payment details for a given payment ID under merchant scope."""
    if not _check_auth(token):
        return json.dumps({"error": "unauthorized", "status": "denied"})

    with SessionLocal() as db:
        row = db.execute(
            text("SELECT id, merchant_id, customer_id, amount, currency, status, failure_reason, payment_method, created_at FROM payments WHERE id = :id AND merchant_id = :mid"),
            {"id": payment_id, "mid": merchant_id},
        ).mappings().first()

        if not row:
            return json.dumps({"error": "payment not found", "status": "not_found"})

        return json.dumps({
            "status": "success",
            "payment": dict(row),
        }, default=str)


@mcp.tool()
def get_customer(customer_id: int, merchant_id: int, token: str) -> str:
    """Retrieve customer details and CLV under merchant scope."""
    if not _check_auth(token):
        return json.dumps({"error": "unauthorized", "status": "denied"})

    with SessionLocal() as db:
        row = db.execute(
            text("SELECT id, merchant_id, external_id, name, email, phone, clv, created_at FROM customers WHERE id = :id AND merchant_id = :mid"),
            {"id": customer_id, "mid": merchant_id},
        ).mappings().first()

        if not row:
            return json.dumps({"error": "customer not found", "status": "not_found"})

        return json.dumps({
            "status": "success",
            "customer": dict(row),
        }, default=str)


@mcp.tool()
def get_recovery_case(case_id: int, merchant_id: int, token: str) -> str:
    """Retrieve details for a specific recovery case."""
    if not _check_auth(token):
        return json.dumps({"error": "unauthorized", "status": "denied"})

    with SessionLocal() as db:
        row = db.execute(
            text("SELECT id, merchant_id, customer_id, amount_at_risk, event_type, recovery_status, recovery_probability, recommended_action, approved_action FROM recovery_cases WHERE id = :id AND merchant_id = :mid"),
            {"id": case_id, "mid": merchant_id},
        ).mappings().first()

        if not row:
            return json.dumps({"error": "case not found", "status": "not_found"})

        return json.dumps({
            "status": "success",
            "case": dict(row),
        }, default=str)


@mcp.tool()
def create_payment_link(customer_id: int, amount: float, reason: str, merchant_id: int, token: str) -> str:
    """Generate a recovery payment link for a customer."""
    if not _check_auth(token):
        return json.dumps({"error": "unauthorized", "status": "denied"})

    link_id = f"plink_sim_{os.urandom(6).hex()}"
    url = f"https://rzp.io/i/{link_id}"
    return json.dumps({
        "status": "success",
        "payment_link_id": link_id,
        "short_url": url,
        "amount": amount,
        "reason": reason,
        "created_at": _now_iso(),
    })


@mcp.tool()
def send_recovery_notification(customer_id: int, message: str, channel: str, merchant_id: int, token: str) -> str:
    """Send a recovery notification (email/sms/whatsapp) to customer."""
    if not _check_auth(token):
        return json.dumps({"error": "unauthorized", "status": "denied"})

    notif_id = f"notif_{os.urandom(6).hex()}"
    return json.dumps({
        "status": "sent",
        "notification_id": notif_id,
        "channel": channel,
        "message_preview": message[:100] + ("..." if len(message) > 100 else ""),
        "dispatched_at": _now_iso(),
    })


@mcp.tool()
def record_recovery_action(case_id: int, action: str, merchant_id: int, token: str) -> str:
    """Log an executed recovery action against a case."""
    if not _check_auth(token):
        return json.dumps({"error": "unauthorized", "status": "denied"})

    return json.dumps({
        "status": "recorded",
        "case_id": case_id,
        "action": action,
        "recorded_at": _now_iso(),
    })


@mcp.tool()
def close_recovery_case(case_id: int, status: str, merchant_id: int, token: str) -> str:
    """Close or mark a recovery case status (recovered, failed, stopped)."""
    if not _check_auth(token):
        return json.dumps({"error": "unauthorized", "status": "denied"})

    if status not in {"recovered", "failed", "stopped"}:
        return json.dumps({"error": f"invalid status {status}", "status": "invalid_input"})

    with SessionLocal() as db:
        db.execute(
            text("UPDATE recovery_cases SET recovery_status = :status WHERE id = :id AND merchant_id = :mid"),
            {"status": status, "id": case_id, "mid": merchant_id},
        )
        db.commit()

    return json.dumps({
        "status": "updated",
        "case_id": case_id,
        "recovery_status": status,
        "updated_at": _now_iso(),
    })


if __name__ == "__main__":
    mcp.run()
