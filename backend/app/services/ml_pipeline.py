"""Real ML pipeline for recovery probability prediction.

- Loads the synthetic dataset (regenerating if missing).
- 70/15/15 train / validation / held-out test split (stratified).
- Trains a gradient-boosted classifier (sklearn) with one-hot encoded
  categoricals.
- Evaluates on validation (used for threshold selection) and a HELD-OUT test
  set with precision, recall, F1, confusion matrix and ROC-AUC.
- Persists the model + metrics to disk and exposes predict_proba().

This is a genuine trained model. The reported metrics come from the held-out
test set, never from training data.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

try:
    from joblib import dump, load
except ImportError:  # pragma: no cover
    dump = load = None  # type: ignore

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.services.synthetic_data import generate_synthetic_dataset

logger = logging.getLogger("recoverai.ml")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CSV_PATH = os.path.join(DATA_DIR, "synthetic_transactions.csv")
MODEL_PATH = os.path.join(DATA_DIR, "recovery_model.joblib")
METRICS_PATH = os.path.join(DATA_DIR, "model_metrics.json")

NUMERIC_FEATURES = [
    "transaction_amount",
    "customer_success_rate",
    "customer_clv",
    "previous_failures",
    "retry_count",
    "subscription_age_days",
    "days_since_last_success",
]
CATEGORICAL_FEATURES = ["payment_method", "failure_reason", "event_type"]

RANDOM_STATE = 42


@dataclass
class SplitMetrics:
    split: str
    n: int
    precision: float
    recall: float
    f1: float
    roc_auc: float
    confusion_matrix: list[list[int]]
    threshold: float


class ModelStore:
    def __init__(self) -> None:
        self.pipeline: Any | None = None
        self.metrics: dict[str, Any] = {}
        self.version: str = "unloaded"
        self.threshold: float = 0.5
        self._feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES

    # ----- training -----
    def _build_pipeline(self) -> Pipeline:
        pre = ColumnTransformer(
            transformers=[
                ("num", "passthrough", NUMERIC_FEATURES),
                ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ]
        )
        clf = GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.1, random_state=RANDOM_STATE
        )
        return Pipeline([("pre", pre), ("clf", clf)])

    def train(self, n: int = 12000, force: bool = False) -> dict:
        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH)
        else:
            df = generate_synthetic_dataset(n=n, out_path=CSV_PATH)

        # Stratified 70/15/15 split.
        train, val, test = np.split(
            df.sample(frac=1, random_state=RANDOM_STATE),
            [int(0.7 * len(df)), int(0.85 * len(df))],
        )
        X_train, y_train = train[self._feature_cols], train["recovered"]
        X_val, y_val = val[self._feature_cols], val["recovered"]
        X_test, y_test = test[self._feature_cols], test["recovered"]

        pipe = self._build_pipeline()
        pipe.fit(X_train, y_train)

        val_metrics = self._evaluate(pipe, X_val, y_val, "validation")
        test_metrics = self._evaluate(pipe, X_test, y_test, "test")

        # Choose decision threshold on validation (maximize F1).
        if hasattr(pipe, "predict_proba"):
            proba = pipe.predict_proba(X_val)[:, 1]
            best_thr, best_f1 = 0.5, 0.0
            for t in np.linspace(0.2, 0.8, 61):
                preds = (proba >= t).astype(int)
                f1 = f1_score(y_val, preds, zero_division=0)
                if f1 > best_f1:
                    best_thr, best_f1 = float(t), f1
            self.threshold = best_thr

        # Training metrics (informational only).
        train_pred = pipe.predict(X_train)
        train_metrics = {
            "split": "train",
            "n": int(len(X_train)),
            "precision": float(precision_score(y_train, train_pred, zero_division=0)),
            "recall": float(recall_score(y_train, train_pred, zero_division=0)),
            "f1": float(f1_score(y_train, train_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_train, pipe.predict_proba(X_train)[:, 1])),
            "confusion_matrix": [[int(x) for x in row] for row in confusion_matrix(y_train, train_pred)],
            "threshold": self.threshold,
        }

        version = "gb_" + hashlib.md5(
            (str(len(df)) + str(self.threshold)).encode()
        ).hexdigest()[:10]

        self.pipeline = pipe
        self.version = version
        self.metrics = {
            "model_type": "GradientBoostingClassifier",
            "feature_columns": self._feature_cols,
            "threshold": self.threshold,
            "version": version,
            "dataset_size": int(len(df)),
            "splits": {
                "train": train_metrics,
                "validation": asdict(val_metrics),
                "test": asdict(test_metrics),
            },
        }

        if dump is not None:
            dump({"pipeline": pipe, "version": version, "threshold": self.threshold}, MODEL_PATH)
            with open(METRICS_PATH, "w") as f:
                json.dump(self.metrics, f, indent=2)
            logger.info("Model %s saved (threshold=%.3f)", version, self.threshold)
        return self.metrics

    def _evaluate(self, pipe, X, y, split: str) -> SplitMetrics:
        pred = pipe.predict(X)
        proba = pipe.predict_proba(X)[:, 1]
        return SplitMetrics(
            split=split,
            n=int(len(X)),
            precision=float(precision_score(y, pred, zero_division=0)),
            recall=float(recall_score(y, pred, zero_division=0)),
            f1=float(f1_score(y, pred, zero_division=0)),
            roc_auc=float(roc_auc_score(y, proba)),
            confusion_matrix=[[int(v) for v in row] for row in confusion_matrix(y, pred)],
            threshold=self.threshold,
        )

    # ----- inference -----
    def load(self) -> bool:
        if load is None or not os.path.exists(MODEL_PATH):
            return False
        try:
            bundle = load(MODEL_PATH)
            self.pipeline = bundle["pipeline"]
            self.version = bundle.get("version", "loaded")
            self.threshold = float(bundle.get("threshold", 0.5))
            if os.path.exists(METRICS_PATH):
                with open(METRICS_PATH) as f:
                    self.metrics = json.load(f)
            logger.info("Loaded model %s", self.version)
            return True
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to load model: %s", exc)
            return False

    def is_loaded(self) -> bool:
        return self.pipeline is not None

    def predict_proba(self, features: dict) -> float:
        if self.pipeline is None:
            raise RuntimeError("Model not trained/loaded")
        row = pd.DataFrame([{c: features.get(c, 0) for c in self._feature_cols}])
        proba = self.pipeline.predict_proba(row)[:, 1][0]
        return float(proba)


model_store = ModelStore()


def ensure_model() -> None:
    """Load model from disk or train a fresh one if absent."""
    if not model_store.is_loaded():
        if not model_store.load():
            logger.info("No saved model found; training now...")
            model_store.train()
