"""Analytics router: business recovery metrics + model evaluation metrics."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.orchestrator import compute_analytics
from app.database import get_db
from app.security import AuthUser, get_current_user
from app.services.ml_pipeline import model_store
from app.schemas.api import AnalyticsOut, MLMetricsOut

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/recovery", response_model=AnalyticsOut)
def recovery_analytics(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)) -> AnalyticsOut:
    return AnalyticsOut(**compute_analytics(db, user.merchant_id))


@router.get("/model", response_model=MLMetricsOut)
def model_metrics() -> MLMetricsOut:
    if not model_store.is_loaded():
        model_store.load()
    m = model_store.metrics or {}
    return MLMetricsOut(
        model_type=m.get("model_type", "GradientBoostingClassifier"),
        version=m.get("version", model_store.version),
        dataset_size=m.get("dataset_size", 0),
        threshold=m.get("threshold", model_store.threshold),
        train=m.get("splits", {}).get("train", {}),
        validation=m.get("splits", {}).get("validation", {}),
        test=m.get("splits", {}).get("test", {}),
    )
