"""Razorpay webhook ingestion & local simulation.

Validates webhook signatures, enforces idempotency (via razorpay_event_id),
persists raw revenue events, and triggers the agent recovery pipeline.
Works in Razorpay TEST MODE and local simulated mode with zero real money moved.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.base import AgentContext
from app.agents.detection import DetectionAgent
from app.agents.orchestrator import process_case
from app.agents.verification import VerificationAgent
from app.config import settings
from app.database import get_db
from app.logging_setup import logger
from app.mcp.gateway import MCPGateway
from app.models.payments import Order, Payment, RevenueEvent
from app.models.users import Customer
from app.models.recovery import RecoveryCase
from app.security import AuthUser, get_current_user
from app.services.llm import get_llm
from app.services.razorpay_client import razorpay_client

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookSimulateRequest(BaseModel):
    event_type: str = "payment.failed"  # payment.failed | payment.captured | order.paid
    amount: float = 3500.0
    currency: str = "INR"
    failure_reason: str | None = "insufficient_funds"
    payment_method: str | None = "card"
    customer_name: str = "Simulated Customer"
    customer_email: str = "simulated.customer@example.com"
    customer_phone: str = "9876543210"
    razorpay_payment_id: str | None = None
    razorpay_order_id: str | None = None


@router.post("/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)) -> Response:
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if settings.RAZORPAY_ENABLED and settings.RAZORPAY_WEBHOOK_SECRET:
        if not razorpay_client.verify_webhook_signature(body, signature):
            logger.warning("Rejected webhook with invalid signature")
            return Response(status_code=status.HTTP_400_BAD_REQUEST, content="invalid signature")

    try:
        payload = json.loads(body.decode("utf-8") if body else "{}")
    except json.JSONDecodeError:
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="bad json")

    event_type = payload.get("event", "")
    entity_payment = payload.get("payload", {}).get("payment", {}).get("entity")
    entity_order = payload.get("payload", {}).get("order", {}).get("entity")
    entity = entity_payment or entity_order or {}

    event_id = payload.get("id") or entity.get("id") or f"evt_{uuid.uuid4().hex[:12]}"

    # Idempotency: skip if we've already processed this event id.
    if db.query(RevenueEvent).filter_by(razorpay_event_id=event_id).first():
        logger.info("Webhook event %s already processed (idempotent skip)", event_id)
        return Response(status_code=status.HTTP_200_OK, content="already processed")

    mid = settings.WEBHOOK_MERCHANT_ID
    amount = float(entity.get("amount", 0)) / 100.0 if entity.get("amount") else 0.0

    rev = RevenueEvent(
        merchant_id=mid,
        event_type=event_type,
        amount=amount,
        currency=entity.get("currency", "INR"),
        razorpay_event_id=event_id,
        payload=json.dumps(payload),
        status="processed",
    )
    db.add(rev)
    db.commit()
    db.refresh(rev)

    if event_type == "payment.failed":
        _handle_payment_failed(db, mid, entity, rev)
    elif event_type == "payment.captured":
        _handle_payment_captured(db, mid, entity, rev)
    elif event_type == "order.paid":
        _handle_order_paid(db, mid, entity, rev)

    return Response(status_code=status.HTTP_200_OK, content="ok")


@router.post("/simulate")
def simulate_webhook(
    body: WebhookSimulateRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Local webhook simulation endpoint allowing testing without external tunnels."""
    mid = user.merchant_id
    event_id = f"evt_sim_{uuid.uuid4().hex[:14]}"
    amount_paise = int(round(body.amount * 100))

    if body.event_type == "order.paid":
        order_id = body.razorpay_order_id or f"order_sim_{uuid.uuid4().hex[:10]}"
        payload = {
            "entity": "event",
            "account_id": "acc_sim_recoverai",
            "event": "order.paid",
            "contains": ["order"],
            "payload": {
                "order": {
                    "entity": {
                        "id": order_id,
                        "entity": "order",
                        "amount": amount_paise,
                        "currency": body.currency,
                        "status": "paid",
                    }
                }
            },
            "created_at": int(datetime.now(timezone.utc).timestamp()),
        }
        entity = payload["payload"]["order"]["entity"]
        rev = RevenueEvent(
            merchant_id=mid,
            event_type="order.paid",
            amount=body.amount,
            currency=body.currency,
            razorpay_event_id=event_id,
            payload=json.dumps(payload),
            status="processed",
        )
        db.add(rev)
        db.commit()
        _handle_order_paid(db, mid, entity, rev)

    elif body.event_type == "payment.captured":
        pay_id = body.razorpay_payment_id or f"pay_sim_{uuid.uuid4().hex[:10]}"
        payload = {
            "entity": "event",
            "account_id": "acc_sim_recoverai",
            "event": "payment.captured",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "entity": "payment",
                        "amount": amount_paise,
                        "currency": body.currency,
                        "status": "captured",
                        "method": body.payment_method or "card",
                    }
                }
            },
            "created_at": int(datetime.now(timezone.utc).timestamp()),
        }
        entity = payload["payload"]["payment"]["entity"]
        rev = RevenueEvent(
            merchant_id=mid,
            event_type="payment.captured",
            amount=body.amount,
            currency=body.currency,
            razorpay_event_id=event_id,
            payload=json.dumps(payload),
            status="processed",
        )
        db.add(rev)
        db.commit()
        _handle_payment_captured(db, mid, entity, rev)

    else:  # payment.failed
        pay_id = body.razorpay_payment_id or f"pay_sim_{uuid.uuid4().hex[:10]}"
        payload = {
            "entity": "event",
            "account_id": "acc_sim_recoverai",
            "event": "payment.failed",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "entity": "payment",
                        "amount": amount_paise,
                        "currency": body.currency,
                        "status": "failed",
                        "method": body.payment_method or "card",
                        "error_reason": body.failure_reason or "insufficient_funds",
                        "customer": {
                            "id": f"cust_sim_{uuid.uuid4().hex[:8]}",
                            "name": body.customer_name,
                            "email": body.customer_email,
                            "contact": body.customer_phone,
                        },
                    }
                }
            },
            "created_at": int(datetime.now(timezone.utc).timestamp()),
        }
        entity = payload["payload"]["payment"]["entity"]
        rev = RevenueEvent(
            merchant_id=mid,
            event_type="payment.failed",
            amount=body.amount,
            currency=body.currency,
            razorpay_event_id=event_id,
            payload=json.dumps(payload),
            status="processed",
        )
        db.add(rev)
        db.commit()
        _handle_payment_failed(db, mid, entity, rev)

    return {
        "status": "simulated",
        "event_id": event_id,
        "event_type": body.event_type,
        "amount": body.amount,
        "currency": body.currency,
    }


def _handle_payment_failed(db: Session, mid: int, entity: dict, rev: RevenueEvent) -> None:
    rz_id = entity.get("id")
    customer = entity.get("customer", {}) or {}
    external_id = str(customer.get("id", f"rz_{rz_id}"))

    c = db.query(Customer).filter_by(merchant_id=mid, external_id=external_id).first()
    if not c:
        c = Customer(
            merchant_id=mid,
            external_id=external_id,
            name=customer.get("name", "Razorpay Customer"),
            email=customer.get("email", ""),
            phone=str(customer.get("contact", "")),
        )
        db.add(c)
        db.commit()
        db.refresh(c)

    p = db.query(Payment).filter_by(merchant_id=mid, razorpay_payment_id=rz_id).first()
    if not p:
        p = Payment(
            merchant_id=mid,
            customer_id=c.id,
            amount=rev.amount,
            currency=entity.get("currency", "INR"),
            status="failed",
            failure_reason=entity.get("error_reason") or entity.get("error", {}).get("reason") or "card_declined",
            payment_method=entity.get("method", "card"),
            razorpay_payment_id=rz_id,
        )
        db.add(p)
        db.commit()
        db.refresh(p)

    rev.customer_id = c.id
    rev.payment_id = p.id
    db.commit()

    gateway = MCPGateway(db, mid, caller="webhook")
    ctx = AgentContext(db, mid, get_llm(), gateway)
    case = DetectionAgent(ctx).detect_failed_payment(p, reason=p.failure_reason)
    process_case(db, case, simulated_outcome=None, auto_approve=False)


def _handle_payment_captured(db: Session, mid: int, entity: dict, rev: RevenueEvent) -> None:
    rz_id = entity.get("id")
    p = db.query(Payment).filter_by(merchant_id=mid, razorpay_payment_id=rz_id).first()
    if p:
        p.status = "captured"
        p.captured_at = datetime.now(timezone.utc)
        rev.payment_id = p.id
        db.commit()

        case = db.query(RecoveryCase).filter_by(merchant_id=mid, payment_id=p.id, recovery_status="open").first()
        if case:
            gateway = MCPGateway(db, mid, caller="webhook")
            ctx = AgentContext(db, mid, get_llm(), gateway)
            VerificationAgent(ctx).run(case, simulated_outcome="success")


def _handle_order_paid(db: Session, mid: int, entity: dict, rev: RevenueEvent) -> None:
    order_id = entity.get("id")
    payment = db.query(Payment).filter_by(merchant_id=mid, razorpay_order_id=order_id).first()
    if payment:
        payment.status = "captured"
        payment.captured_at = datetime.now(timezone.utc)
        rev.customer_id = payment.customer_id
        rev.payment_id = payment.id
        order = db.query(Order).filter_by(merchant_id=mid, id=payment.order_id).first() if payment.order_id else None
        if order:
            order.status = "paid"
        db.commit()

        case = db.query(RecoveryCase).filter_by(merchant_id=mid, payment_id=payment.id, recovery_status="open").first()
        if case:
            gateway = MCPGateway(db, mid, caller="webhook")
            ctx = AgentContext(db, mid, get_llm(), gateway)
            VerificationAgent(ctx).run(case, simulated_outcome="success")
