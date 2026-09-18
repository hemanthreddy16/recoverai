"""Payment management router with merchant scoping and failure tracking."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.agents.base import AgentContext
from app.agents.detection import DetectionAgent
from app.database import get_db
from app.mcp.gateway import MCPGateway
from app.models.payments import Order, Payment
from app.models.recovery import RecoveryCase
from app.models.users import Customer
from app.schemas.api import PaymentCreate, PaymentOut, RazorpayOrderCreate, RazorpayOrderOut, RazorpayVerifyRequest
from app.security import AuthUser, get_current_user, require_role
from app.services.llm import get_llm
from app.services.razorpay_client import razorpay_client

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


@router.post("/{payment_id}/razorpay/order", response_model=RazorpayOrderOut)
def create_razorpay_checkout_order(
    payment_id: int,
    body: RazorpayOrderCreate | None = None,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> RazorpayOrderOut:
    """Create a Razorpay Checkout order for an existing failed/open payment."""
    if not razorpay_client.is_enabled():
        raise HTTPException(status_code=503, detail="Razorpay is disabled. Enable RAZORPAY_ENABLED with test keys.")

    payment = db.query(Payment).filter_by(id=payment_id, merchant_id=user.merchant_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status == "captured":
        raise HTTPException(status_code=400, detail="Payment is already captured")

    customer = db.query(Customer).filter_by(id=payment.customer_id, merchant_id=user.merchant_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Reuse an existing internal order only if it is still unpaid.
    order = db.query(Order).filter_by(id=payment.order_id, merchant_id=user.merchant_id).first() if payment.order_id else None
    if not order:
        order = Order(merchant_id=user.merchant_id, customer_id=customer.id, amount=payment.amount, currency=payment.currency, status="created")
        db.add(order)
        db.commit()
        db.refresh(order)
        payment.order_id = order.id

    rp_order = razorpay_client.create_order(
        payment.amount, payment.currency, receipt=f"recoverai_p{payment.id}",
    )
    payment.razorpay_order_id = rp_order["id"]
    db.commit()

    return RazorpayOrderOut(
        payment_id=payment.id,
        razorpay_order_id=rp_order["id"],
        amount=payment.amount,
        currency=payment.currency,
        key_id=razorpay_client.key_id,
        name="RecoverAI",
        description=f"Payment recovery #{payment.id}",
    )


@router.post("/{payment_id}/razorpay/verify", response_model=PaymentOut)
def verify_razorpay_checkout(
    payment_id: int,
    body: RazorpayVerifyRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> Payment:
    """Verify Checkout signature server-side and mark the payment captured."""
    payment = (
        db.query(Payment)
        .filter_by(id=payment_id, merchant_id=user.merchant_id)
        .first()
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.razorpay_order_id != body.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Razorpay order mismatch")

    if not razorpay_client.verify_payment_signature(
        body.razorpay_order_id,
        body.razorpay_payment_id,
        body.razorpay_signature,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay payment signature",
        )

    payment.razorpay_payment_id = body.razorpay_payment_id
    payment.status = "captured"
    payment.captured_at = datetime.now(timezone.utc)

    # Mark the linked recovery case as recovered after successful payment.
    case = (
        db.query(RecoveryCase)
        .filter_by(
            payment_id=payment.id,
            merchant_id=user.merchant_id,
        )
        .first()
    )

    if case and case.recovery_status != "recovered":
        case.recovery_status = "recovered"
        case.action_status = "executed"
        case.amount_recovered = payment.amount
        case.resolved_at = datetime.now(timezone.utc)

    order = (
        db.query(Order)
        .filter_by(
            id=payment.order_id,
            merchant_id=user.merchant_id,
        )
        .first()
        if payment.order_id
        else None
    )

    if order:
        order.status = "paid"

    db.commit()
    db.refresh(payment)

    return payment