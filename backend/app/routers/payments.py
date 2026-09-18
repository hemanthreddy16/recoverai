"""Payment management router with merchant scoping and failure tracking."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.agents.base import AgentContext
from app.agents.detection import DetectionAgent
from app.database import get_db
from app.mcp.gateway import MCPGateway
from app.models.payments import Payment
from app.models.users import Customer
from app.schemas.api import PaymentCreate, PaymentOut
from app.security import AuthUser, get_current_user, require_role
from app.services.llm import get_llm

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=list[PaymentOut])
def list_payments(
    status_filter: str | None = Query(None, alias="status"),
    failure_reason: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> list[Payment]:
    query = db.query(Payment).filter_by(merchant_id=user.merchant_id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if failure_reason:
        query = query.filter_by(failure_reason=failure_reason)
    return query.order_by(Payment.created_at.desc()).offset(offset).limit(limit).all()


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    body: PaymentCreate,
    trigger_detection: bool = Query(True, description="Whether to trigger automated detection agent for failed payments"),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> Payment:
    customer = (
        db.query(Customer)
        .filter_by(id=body.customer_id, merchant_id=user.merchant_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    payment = Payment(
        merchant_id=user.merchant_id,
        customer_id=body.customer_id,
        amount=body.amount,
        currency=body.currency,
        status=body.status,
        failure_reason=body.failure_reason,
        payment_method=body.payment_method,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if trigger_detection and payment.status == "failed":
        gateway = MCPGateway(db, user.merchant_id, caller="payment_api")
        ctx = AgentContext(db, user.merchant_id, get_llm(), gateway)
        DetectionAgent(ctx).detect_failed_payment(payment, reason=payment.failure_reason)

    return payment


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> Payment:
    payment = (
        db.query(Payment)
        .filter_by(id=payment_id, merchant_id=user.merchant_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment
