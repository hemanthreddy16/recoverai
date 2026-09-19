# Resurge Model Context Protocol (MCP) Server

The **Resurge MCP Server** provides a secure, audited execution layer between intelligent agents and payment infrastructure.

## Security Architecture

1. **Token Authorization**: Every tool invocation requires a valid `token` matching `MCP_AUTH_TOKEN`.
2. **Merchant Multi-Tenancy**: All queries and mutations are strictly filtered by `merchant_id`.
3. **Audit Logging**: Sensitive actions (payment links, notifications, retries) are tracked in the database audit log.
4. **Safe Simulation Mode**: In development/testing, tools simulate gateway actions without moving real funds.

## Available Tools

- `ping()` / `health_check(token)`: Liveness & database connection status.
- `get_payment(payment_id, merchant_id, token)`: Fetch payment details.
- `get_customer(customer_id, merchant_id, token)`: Fetch customer & CLV data.
- `get_recovery_case(case_id, merchant_id, token)`: Read case status.
- `create_payment_link(customer_id, amount, reason, merchant_id, token)`: Generate payment recovery links.
- `send_recovery_notification(customer_id, message, channel, merchant_id, token)`: Dispatch customer communication.
- `record_recovery_action(case_id, action, merchant_id, token)`: Log remediation steps.
- `close_recovery_case(case_id, status, merchant_id, token)`: Update case lifecycle.

## Running Locally

```bash
cd mcp_server
pip install -r requirements.txt
python server.py
```

## Running Tests

```bash
pytest test_mcp.py
```
