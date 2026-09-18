"""ML pipeline router: prediction service, training trigger, and metrics.

Exposes the trained GradientBoosting model through REST endpoints for
ad-hoc scoring, retraining, and evaluation metric retrieval.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.api import (
    MLMetricsOut,
    PredictRequest,
    PredictResponse,
    TrainResponse,
)
from app.security import AuthUser, get_current_user, require_role
from app.services.ml_pipeline import model_store, ensure_model

router = APIRouter(prefix="/ml", tags=["ml"])


@router.post("/predict", response_model=PredictResponse)
def predict(
    body: PredictRequest,
    user: AuthUser = Depends(get_current_user),
) -> PredictResponse:
    """Score a payment scenario and return the recovery probability."""
    if not model_store.is_loaded():
        ensure_model()
    if not model_store.is_loaded():
        raise HTTPException(status_code=503, detail="Model not available")

    features = body.model_dump()
    proba = model_store.predict_proba(features)
    return PredictResponse(
        recovery_probability=round(proba, 4),
        will_recover=proba >= model_store.threshold,
        model_version=model_store.version,
        threshold=model_store.threshold,
        features_used=features,
    )


@router.post("/train", response_model=TrainResponse)
def train(
    user: AuthUser = Depends(require_role("admin")),
) -> TrainResponse:
    """Retrain the model on the synthetic dataset (admin only)."""
    metrics = model_store.train(n=12000, force=True)
    return TrainResponse(
        status="trained",
        model_version=metrics.get("version", model_store.version),
        dataset_size=metrics.get("dataset_size", 0),
        threshold=metrics.get("threshold", model_store.threshold),
        train=metrics.get("splits", {}).get("train", {}),
        validation=metrics.get("splits", {}).get("validation", {}),
        test=metrics.get("splits", {}).get("test", {}),
    )


@router.get("/metrics", response_model=MLMetricsOut)
def metrics(
    user: AuthUser = Depends(get_current_user),
) -> MLMetricsOut:
    """Return full evaluation metrics (precision, recall, F1, ROC-AUC, confusion matrix)."""
    if not model_store.is_loaded():
        ensure_model()
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
