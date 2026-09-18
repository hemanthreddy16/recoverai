"""Root + health endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.common import HealthResponse
from app.security import AuthUser, get_current_user

router = APIRouter(tags=["root"])


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    from app.services.ml_pipeline import model_store

    return HealthResponse(
        status="ok",
        version="1.0.0",
        ml_model_loaded=model_store.is_loaded(),
        razorpay_enabled=settings.RAZORPAY_ENABLED,
    )


@router.get("/me/context")
def my_context(user: AuthUser = Depends(get_current_user)) -> dict:
    return {
        "user_id": user.user_id,
        "merchant_id": user.merchant_id,
        "role": user.role,
        "email": user.email,
    }
