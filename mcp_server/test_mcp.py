"""MCP Server unit tests and health verification."""
import json
import pytest
from server import health_check, ping, create_payment_link, send_recovery_notification, get_payment, MCP_AUTH_TOKEN


def test_ping():
    res = json.loads(ping())
    assert res["status"] == "pong"
    assert "timestamp" in res


def test_health_check():
    res = json.loads(health_check())
    assert res["service"] == "recoverai-mcp-server"
    assert "status" in res
    assert "database_connected" in res


def test_auth_rejection():
    res = json.loads(create_payment_link(1, 1500.0, "Testing unauthorized", 1, "wrong-token"))
    assert res["status"] == "denied"
    assert res["error"] == "unauthorized"


def test_create_payment_link_authorized():
    res = json.loads(create_payment_link(1, 2500.0, "Payment Recovery Link", 1, MCP_AUTH_TOKEN))
    assert res["status"] == "success"
    assert "payment_link_id" in res
    assert "short_url" in res


def test_send_notification_authorized():
    res = json.loads(send_recovery_notification(1, "Your payment retry was successful", "email", 1, MCP_AUTH_TOKEN))
    assert res["status"] == "sent"
    assert "notification_id" in res
