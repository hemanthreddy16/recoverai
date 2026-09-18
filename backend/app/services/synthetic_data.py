"""Synthetic payment dataset generation (>=10,000 transactions).

Generates a realistic, reproducible dataset of failed/recoverable/non-recoverable
payments with engineered features and a recovery label. The label is generated
from a transparent probabilistic model so the ML pipeline has genuine signal to
learn (no leaking of the label into trivial features).

Output: a CSV at backend/data/synthetic_transactions.csv used by the ML pipeline
for training/validation/held-out test.
"""
from __future__ import annotations

import os
from typing import Literal

import numpy as np
import pandas as pd

# Failure reason taxonomy. Each reason maps to a base recoverability.
FAILURE_REASONS: dict[str, float] = {
    "insufficient_funds": 0.72,      # recoverable: retry after payday
    "network_error": 0.80,           # recoverable: transient
    "timeout": 0.78,                 # recoverable: transient
    "card_declined": 0.45,           # mixed
    "incorrect_cvv": 0.60,           # recoverable after correction
    "expired_card": 0.35,            # needs action, less automatic
    "payment_cancelled": 0.20,       # user cancelled -> low
    "fraud_blocked": 0.08,           # essentially non-recoverable automatically
    "subscription_hard_fail": 0.30,  # churn-ish
    "authentication_failed": 0.55,
}

PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet", "emandate"]
METHOD_RECOVERY_BONUS = {
    "card": 0.0, "upi": 0.05, "netbanking": -0.02,
    "wallet": 0.03, "emandate": -0.10,
}

EVENT_TYPES = ["payment_failed", "checkout_abandoned", "subscription_failed", "overdue_receivable"]


def _base_recovery_prob(row: dict) -> float:
    """Transparent ground-truth generator (NOT the model; used to label data)."""
    p = FAILURE_REASONS.get(row["failure_reason"], 0.4)
    p += METHOD_RECOVERY_BONUS.get(row["payment_method"], 0.0)
    # Historical success rate strongly helps.
    p += (row["customer_success_rate"] - 0.5) * 0.5
    # Previous failures hurt.
    p -= row["previous_failures"] * 0.06
    # Retry count: mild positive up to a point, then negative.
    p += min(row["retry_count"], 2) * 0.04
    if row["retry_count"] > 3:
        p -= (row["retry_count"] - 3) * 0.08
    # Days since last success: long gap hurts slightly.
    p -= min(row["days_since_last_success"], 60) / 60 * 0.06
    # Subscription age: longer tenure slightly more loyal.
    p += min(row["subscription_age_days"], 365) / 365 * 0.04
    # Amount: very large amounts slightly harder to recover automatically.
    if row["transaction_amount"] > 50000:
        p -= 0.06
    return float(np.clip(p, 0.02, 0.98))


def generate_synthetic_dataset(
    n: int = 12000, seed: int = 42, out_path: str | None = None
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    reason_keys = list(FAILURE_REASONS.keys())
    for i in range(n):
        # Customer-level latent traits.
        cust_success = float(np.clip(rng.normal(0.62, 0.18), 0.02, 0.99))
        clv = float(np.clip(rng.lognormal(mean=8.0, sigma=0.8), 50, 200000))
        sub_age = int(rng.integers(0, 720))
        prev_fail = int(rng.poisson(1.1))
        retry = int(rng.poisson(0.8))
        days_gap = int(rng.integers(0, 75))
        amount = float(np.clip(rng.lognormal(mean=7.6, sigma=0.9), 20, 250000))
        method = rng.choice(PAYMENT_METHODS, p=[0.5, 0.25, 0.1, 0.1, 0.05])
        reason = rng.choice(reason_keys, p=_reason_probs(rng))
        event_type = _event_for_reason(reason, rng)
        feat = {
            "transaction_amount": round(amount, 2),
            "customer_success_rate": round(cust_success, 4),
            "customer_clv": round(clv, 2),
            "previous_failures": prev_fail,
            "retry_count": retry,
            "payment_method": method,
            "failure_reason": reason,
            "subscription_age_days": sub_age,
            "days_since_last_success": days_gap,
            "event_type": event_type,
        }
        true_p = _base_recovery_prob(feat)
        # Label: 1 if a Bernoulli draw with true_p succeeds.
        recovered = int(rng.random() < true_p)
        feat["recovery_probability_true"] = round(true_p, 4)
        feat["recovered"] = recovered
        rows.append(feat)

    df = pd.DataFrame(rows)
    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        df.to_csv(out_path, index=False)
    return df


def _reason_probs(rng) -> list[float]:
    # Rough prevalence distribution; stable across calls.
    return [0.22, 0.10, 0.08, 0.14, 0.08, 0.07, 0.10, 0.06, 0.08, 0.07]


def _event_for_reason(reason: str, rng) -> str:
    if reason in ("subscription_hard_fail",):
        return "subscription_failed"
    if reason in ("payment_cancelled",):
        return rng.choice(EVENT_TYPES, p=[0.3, 0.4, 0.2, 0.1])
    return rng.choice(EVENT_TYPES, p=[0.5, 0.2, 0.15, 0.15])


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(here, "data", "synthetic_transactions.csv")
    df = generate_synthetic_dataset(n=12000, out_path=path)
    print(f"Wrote {len(df)} rows -> {path}")
    print(df["recovered"].value_counts(normalize=True).to_dict())
