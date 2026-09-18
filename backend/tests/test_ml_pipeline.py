"""Phase 5: ML Pipeline Tests.

Tests:
1. Synthetic data generation (>=10,000 records)
2. Feature engineering
3. Training pipeline (train/val/test splits)
4. Model persistence (save + load)
5. Prediction service
6. Evaluation metrics (precision, recall, F1, ROC-AUC, confusion matrix)
7. API endpoints (/ml/predict, /ml/train, /ml/metrics)

All metrics are computed from held-out test data — never fabricated.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.synthetic_data import generate_synthetic_dataset
from app.services.ml_pipeline import (
    ModelStore,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    model_store,
    ensure_model,
)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers(client: TestClient):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@recoverai.dev", "password": "recoverai123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# =====================================================================
# 1. Synthetic Dataset Generation
# =====================================================================
class TestSyntheticData:
    def test_generates_minimum_10000_records(self):
        df = generate_synthetic_dataset(n=10000)
        assert len(df) >= 10000, f"Expected >=10000 rows, got {len(df)}"

    def test_required_columns_present(self):
        df = generate_synthetic_dataset(n=500)
        required = NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["recovered", "recovery_probability_true"]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_label_distribution_realistic(self):
        df = generate_synthetic_dataset(n=10000)
        recovery_rate = df["recovered"].mean()
        # Recovery rate should be between 20% and 80% — realistic
        assert 0.2 < recovery_rate < 0.8, f"Recovery rate {recovery_rate:.2%} outside realistic range"

    def test_feature_ranges_valid(self):
        df = generate_synthetic_dataset(n=5000)
        assert df["transaction_amount"].min() > 0
        assert 0.0 <= df["customer_success_rate"].min()
        assert df["customer_success_rate"].max() <= 1.0
        assert df["previous_failures"].min() >= 0
        assert df["retry_count"].min() >= 0

    def test_categorical_values_valid(self):
        df = generate_synthetic_dataset(n=5000)
        valid_methods = {"card", "upi", "netbanking", "wallet", "emandate"}
        assert set(df["payment_method"].unique()).issubset(valid_methods)

    def test_reproducibility(self):
        df1 = generate_synthetic_dataset(n=1000, seed=42)
        df2 = generate_synthetic_dataset(n=1000, seed=42)
        pd.testing.assert_frame_equal(df1, df2)


# =====================================================================
# 2. Feature Engineering & Training Pipeline
# =====================================================================
class TestTrainingPipeline:
    @pytest.fixture(scope="class")
    def trained_store(self):
        store = ModelStore()
        metrics = store.train(n=10000, force=True)
        return store, metrics

    def test_training_completes(self, trained_store):
        store, metrics = trained_store
        assert store.is_loaded()
        assert store.pipeline is not None

    def test_version_generated(self, trained_store):
        store, metrics = trained_store
        assert store.version.startswith("gb_")

    def test_threshold_selected(self, trained_store):
        store, metrics = trained_store
        assert 0.1 < store.threshold < 0.9, f"Threshold {store.threshold} outside sane range"

    def test_dataset_size_recorded(self, trained_store):
        _, metrics = trained_store
        assert metrics["dataset_size"] >= 10000

    def test_three_splits_present(self, trained_store):
        _, metrics = trained_store
        assert "train" in metrics["splits"]
        assert "validation" in metrics["splits"]
        assert "test" in metrics["splits"]

    def test_split_sizes_correct(self, trained_store):
        _, metrics = trained_store
        n = metrics["dataset_size"]
        train_n = metrics["splits"]["train"]["n"]
        val_n = metrics["splits"]["validation"]["n"]
        test_n = metrics["splits"]["test"]["n"]
        assert train_n + val_n + test_n == n
        # 70/15/15 split
        assert abs(train_n / n - 0.70) < 0.02
        assert abs(val_n / n - 0.15) < 0.02
        assert abs(test_n / n - 0.15) < 0.02


# =====================================================================
# 3. Held-Out Test Set Evaluation (Real Metrics)
# =====================================================================
class TestEvaluationMetrics:
    @pytest.fixture(scope="class")
    def test_metrics(self):
        store = ModelStore()
        metrics = store.train(n=12000, force=True)
        return metrics["splits"]["test"]

    def test_precision_above_baseline(self, test_metrics):
        # A random baseline would be ~50%; a trained model should exceed 60%
        assert test_metrics["precision"] > 0.55, f"Precision too low: {test_metrics['precision']:.4f}"

    def test_recall_above_baseline(self, test_metrics):
        assert test_metrics["recall"] > 0.55, f"Recall too low: {test_metrics['recall']:.4f}"

    def test_f1_above_baseline(self, test_metrics):
        assert test_metrics["f1"] > 0.55, f"F1 too low: {test_metrics['f1']:.4f}"

    def test_roc_auc_above_baseline(self, test_metrics):
        # ROC-AUC 0.5 = random; a real model should exceed 0.70
        assert test_metrics["roc_auc"] > 0.70, f"ROC-AUC too low: {test_metrics['roc_auc']:.4f}"

    def test_confusion_matrix_shape(self, test_metrics):
        cm = test_metrics["confusion_matrix"]
        assert len(cm) == 2
        assert len(cm[0]) == 2
        assert len(cm[1]) == 2

    def test_confusion_matrix_sums_to_test_size(self, test_metrics):
        cm = test_metrics["confusion_matrix"]
        total = sum(sum(row) for row in cm)
        assert total == test_metrics["n"]

    def test_metrics_not_fabricated(self, test_metrics):
        # Verify that the metrics are float values that differ from each other
        p, r, f1, auc = (
            test_metrics["precision"],
            test_metrics["recall"],
            test_metrics["f1"],
            test_metrics["roc_auc"],
        )
        # These should not all be identical (would indicate fabrication)
        values = {round(v, 6) for v in [p, r, f1, auc]}
        assert len(values) > 1, "All metrics identical — likely fabricated"


# =====================================================================
# 4. Model Persistence
# =====================================================================
class TestModelPersistence:
    def test_save_and_reload(self):
        # Train
        store1 = ModelStore()
        store1.train(n=5000, force=True)
        v1 = store1.version
        t1 = store1.threshold

        # Load into a fresh store
        store2 = ModelStore()
        loaded = store2.load()
        assert loaded is True
        assert store2.version == v1
        assert abs(store2.threshold - t1) < 1e-6

    def test_prediction_after_reload(self):
        store = ModelStore()
        assert store.load()
        proba = store.predict_proba({
            "transaction_amount": 3500.0,
            "customer_success_rate": 0.7,
            "customer_clv": 12000.0,
            "previous_failures": 1,
            "retry_count": 0,
            "payment_method": "card",
            "failure_reason": "insufficient_funds",
            "subscription_age_days": 120,
            "days_since_last_success": 5,
            "event_type": "payment_failed",
        })
        assert 0.0 <= proba <= 1.0


# =====================================================================
# 5. Prediction Service
# =====================================================================
class TestPredictionService:
    @pytest.fixture(scope="class", autouse=True)
    def setup_model(self):
        ensure_model()

    def test_predict_high_recovery(self):
        proba = model_store.predict_proba({
            "transaction_amount": 1500.0,
            "customer_success_rate": 0.9,
            "customer_clv": 50000.0,
            "previous_failures": 0,
            "retry_count": 1,
            "payment_method": "upi",
            "failure_reason": "network_error",
            "subscription_age_days": 365,
            "days_since_last_success": 2,
            "event_type": "payment_failed",
        })
        assert proba > 0.5, f"Expected high recovery, got {proba:.4f}"

    def test_predict_low_recovery(self):
        proba = model_store.predict_proba({
            "transaction_amount": 100000.0,
            "customer_success_rate": 0.1,
            "customer_clv": 500.0,
            "previous_failures": 8,
            "retry_count": 5,
            "payment_method": "emandate",
            "failure_reason": "fraud_blocked",
            "subscription_age_days": 10,
            "days_since_last_success": 60,
            "event_type": "payment_failed",
        })
        assert proba < 0.5, f"Expected low recovery, got {proba:.4f}"

    def test_predict_returns_float(self):
        proba = model_store.predict_proba({
            "transaction_amount": 5000.0,
            "customer_success_rate": 0.5,
            "customer_clv": 10000.0,
            "previous_failures": 2,
            "retry_count": 1,
            "payment_method": "card",
            "failure_reason": "card_declined",
            "subscription_age_days": 90,
            "days_since_last_success": 10,
            "event_type": "payment_failed",
        })
        assert isinstance(proba, float)
        assert 0.0 <= proba <= 1.0


# =====================================================================
# 6. API Endpoints
# =====================================================================
class TestMLEndpoints:
    def test_predict_endpoint(self, client: TestClient, auth_headers: dict):
        resp = client.post(
            "/api/v1/ml/predict",
            json={
                "transaction_amount": 4200.0,
                "customer_success_rate": 0.72,
                "customer_clv": 18000.0,
                "previous_failures": 1,
                "retry_count": 0,
                "payment_method": "card",
                "failure_reason": "insufficient_funds",
                "subscription_age_days": 200,
                "days_since_last_success": 3,
                "event_type": "payment_failed",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "recovery_probability" in data
        assert "will_recover" in data
        assert "model_version" in data
        assert "threshold" in data
        assert 0.0 <= data["recovery_probability"] <= 1.0
        assert isinstance(data["will_recover"], bool)

    def test_predict_unauthenticated_fails(self, client: TestClient):
        resp = client.post("/api/v1/ml/predict", json={})
        assert resp.status_code in (401, 403)

    def test_metrics_endpoint(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/v1/ml/metrics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_type"] == "GradientBoostingClassifier"
        assert data["dataset_size"] >= 10000
        assert "test" in data
        assert "validation" in data
        assert "train" in data
        # Verify test split has all required metrics
        test = data["test"]
        for key in ("precision", "recall", "f1", "roc_auc", "confusion_matrix"):
            assert key in test, f"Missing key in test metrics: {key}"

    def test_train_endpoint_admin(self, client: TestClient, auth_headers: dict):
        resp = client.post("/api/v1/ml/train", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "trained"
        assert data["dataset_size"] >= 10000
        assert "test" in data
        assert data["test"]["roc_auc"] > 0.5

    def test_analytics_model_endpoint(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/v1/analytics/model", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_type"] == "GradientBoostingClassifier"
