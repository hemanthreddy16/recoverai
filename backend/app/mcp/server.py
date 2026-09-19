"""Dedicated MCP server (stdio).

Exposes the controlled recovery tools over the Model Context Protocol so that
any MCP-compatible client (including the agent orchestrator in external mode)
can only perform authorized, audited operations. The tool implementations
delegate to app/services/mcp_tools_impl.py — the single source of truth.

Run standalone with:  python -m app.mcp.server
"""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from app.database import SessionLocal
from app.services import mcp_tools_impl
from app.services.mcp_tools_impl import MCPError

mcp = FastMCP("RESURGE-MCP")


def _session():
    return SessionLocal()


def _auth_error() -> dict:
    return {"error": "unauthorized", "status": "denied"}


def _run(tool_name: str, merchant_id: int, token: str, fn) -> str:
    db = _session()
    try:
        tools = mcp_tools_impl.MCPTools(db, merchant_id, caller="mcp_server")
        method = getattr(tools, tool_name)
        # Build kwargs: strip merchant_id from fn by passing through closure.
        result = fn(tools)
        return json.dumps(result)
    except MCPError as e:
        return json.dumps({"error": str(e), "status": e.status})
    finally:
        db.close()


@mcp.tool()
def get_payment(payment_id: int, merchant_id: int, token: str) -> str:
    return _run("get_payment", merchant_id, token, lambda t: t.get_payment(payment_id, token))


@mcp.tool()
def get_customer(customer_id: int, merchant_id: int, token: str) -> str:
    return _run("get_customer", merchant_id, token, lambda t: t.get_customer(customer_id, token))


@mcp.tool()
def get_customer_payment_history(customer_id: int, merchant_id: int, token: str) -> str:
    return _run("get_customer_payment_history", merchant_id, token, lambda t: t.get_customer_payment_history(customer_id, token))


@mcp.tool()
def get_failed_payments(merchant_id: int, token: str) -> str:
    return _run("get_failed_payments", merchant_id, token, lambda t: t.get_failed_payments(token))


@mcp.tool()
def get_recovery_case(case_id: int, merchant_id: int, token: str) -> str:
    return _run("get_recovery_case", merchant_id, token, lambda t: t.get_recovery_case(case_id, token))


@mcp.tool()
def calculate_recovery_score(payment_id: int, merchant_id: int, token: str) -> str:
    return _run("calculate_recovery_score", merchant_id, token, lambda t: t.calculate_recovery_score(payment_id, token))


@mcp.tool()
def create_payment_link(customer_id: int, amount: float, reason: str, merchant_id: int, token: str) -> str:
    return _run("create_payment_link", merchant_id, token, lambda t: t.create_payment_link(customer_id, amount, reason, token))


@mcp.tool()
def schedule_retry(payment_id: int, scheduled_time: str, merchant_id: int, token: str) -> str:
    return _run("schedule_retry", merchant_id, token, lambda t: t.schedule_retry(payment_id, scheduled_time, token))


@mcp.tool()
def send_recovery_notification(customer_id: int, message: str, channel: str, merchant_id: int, token: str) -> str:
    return _run("send_recovery_notification", merchant_id, token, lambda t: t.send_recovery_notification(customer_id, message, channel, token))


@mcp.tool()
def verify_payment(payment_id: int, merchant_id: int, token: str) -> str:
    return _run("verify_payment", merchant_id, token, lambda t: t.verify_payment(payment_id, token))


@mcp.tool()
def record_recovery_action(case_id: int, action: str, merchant_id: int, token: str) -> str:
    return _run("record_recovery_action", merchant_id, token, lambda t: t.record_recovery_action(case_id, action, token))


@mcp.tool()
def close_recovery_case(case_id: int, status: str, merchant_id: int, token: str) -> str:
    return _run("close_recovery_case", merchant_id, token, lambda t: t.close_recovery_case(case_id, status, token))


@mcp.tool()
def get_recovery_metrics(merchant_id: int, token: str) -> str:
    return _run("get_recovery_metrics", merchant_id, token, lambda t: t.get_recovery_metrics(token))


if __name__ == "__main__":
    mcp.run()
