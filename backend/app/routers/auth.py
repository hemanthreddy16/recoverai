"""Authentication router: register, login, current user, role management."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.recovery import MerchantPolicy
from app.models.users import Merchant, User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RoleUpdateRequest,
    TokenResponse,
    UserOut,
)
from app.security import (
    AuthUser,
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _ensure_default_policy(db: Session, merchant_id: int) -> MerchantPolicy:
    policy = db.query(MerchantPolicy).filter_by(merchant_id=merchant_id).first()
    if policy is None:
        policy = MerchantPolicy(merchant_id=merchant_id)
        db.add(policy)
        db.commit()
        db.refresh(policy)
    return policy


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.query(User).filter_by(email=body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # First user of a merchant becomes admin; we create a fresh merchant here.
    slug = body.merchant_name.lower().replace(" ", "-") + "-" + str(abs(hash(body.email)) % 10000)
    merchant = Merchant(name=body.merchant_name, slug=slug)
    db.add(merchant)
    db.commit()
    db.refresh(merchant)

    user = User(
        merchant_id=merchant.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role if body.role in ("admin", "operator", "viewer") else "admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _ensure_default_policy(db, merchant.id)
    token = create_access_token(str(user.id), merchant.id, user.role)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter_by(email=body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    token = create_access_token(str(user.id), user.merchant_id, user.role)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))
@router.post("/token")
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter_by(email=form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    access_token = create_access_token(
        str(user.id),
        user.merchant_id,
        user.role,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserOut)
def me(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    db_user = db.get(User, user.user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(db_user)


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_role(
    user_id: int,
    body: RoleUpdateRequest,
    admin: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> UserOut:
    target = db.query(User).filter_by(id=user_id, merchant_id=admin.merchant_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.role = body.role
    db.commit()
    db.refresh(target)
    return UserOut.model_validate(target)
