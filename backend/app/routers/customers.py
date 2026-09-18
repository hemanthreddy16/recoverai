"""Customer management router with strict merchant isolation."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.payments import Payment
from app.models.recovery import RecoveryCase
from app.models.users import Customer
from app.schemas.api import CaseOut, CustomerCreate, CustomerOut, CustomerUpdate, PaymentOut
from app.security import AuthUser, get_current_user, require_role

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
def list_customers(
    q: str | None = Query(None, description="Search by name, email, or external_id"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> list[Customer]:
    query = db.query(Customer).filter_by(merchant_id=user.merchant_id)
    if q:
        search = f"%{q}%"
        query = query.filter(
            (Customer.name.ilike(search))
            | (Customer.email.ilike(search))
            | (Customer.external_id.ilike(search))
        )
    return query.order_by(Customer.created_at.desc()).offset(offset).limit(limit).all()


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    body: CustomerCreate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> Customer:
    existing = (
        db.query(Customer)
        .filter_by(merchant_id=user.merchant_id, external_id=body.external_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Customer with external_id '{body.external_id}' already exists",
        )

    customer = Customer(
        merchant_id=user.merchant_id,
        external_id=body.external_id,
        name=body.name,
        email=body.email,
        phone=body.phone,
        clv=body.clv,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> Customer:
    customer = (
        db.query(Customer)
        .filter_by(id=customer_id, merchant_id=user.merchant_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role("admin", "operator")),
) -> Customer:
    customer = (
        db.query(Customer)
        .filter_by(id=customer_id, merchant_id=user.merchant_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if body.name is not None:
        customer.name = body.name
    if body.email is not None:
        customer.email = body.email
    if body.phone is not None:
        customer.phone = body.phone
    if body.clv is not None:
        customer.clv = body.clv

    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}/payments", response_model=list[PaymentOut])
def get_customer_payments(
    customer_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> list[Payment]:
    customer = (
        db.query(Customer)
        .filter_by(id=customer_id, merchant_id=user.merchant_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return (
        db.query(Payment)
        .filter_by(customer_id=customer_id, merchant_id=user.merchant_id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{customer_id}/cases", response_model=list[CaseOut])
def get_customer_cases(
    customer_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> list[RecoveryCase]:
    customer = (
        db.query(Customer)
        .filter_by(id=customer_id, merchant_id=user.merchant_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return (
        db.query(RecoveryCase)
        .filter_by(customer_id=customer_id, merchant_id=user.merchant_id)
        .order_by(RecoveryCase.created_at.desc())
        .all()
    )
