"""Razorpay Test Mode client + webhook signature verification.

All credentials come from environment variables. When Razorpay is not enabled
(RAZORPAY_ENABLED=false) the client reports itself disabled and the system uses
a safe local simulation so the demo runs without external accounts.

NO real money is ever moved: this integrates only with Razorpay's TEST mode.
"""
from __future__ import annotations

import hmac
import hashlib
import logging

import httpx

from app.config import settings

logger = logging.getLogger("resurge.razorpay")


class RazorpayClient:
    def __init__(self) -> None:
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        self.enabled = settings.RAZORPAY_ENABLED and bool(self.key_id and self.key_secret)

    def is_enabled(self) -> bool:
        return self.enabled

    # ---------- REST calls (test mode only) ----------
    def _auth(self) -> tuple[str, str]:
        return (self.key_id, self.key_secret)

    def create_payment_link(self, customer, amount: float, reason: str) -> dict:
        if not self.enabled:
            raise RuntimeError("Razorpay not enabled")
        payload = {
            "amount": int(round(amount * 100)),  # paise
            "currency": "INR",
            "description": reason or "Payment recovery",
            "customer": {
                "name": customer.name or "Customer",
                "email": customer.email or "customer@example.com",
                "contact": customer.phone or "9999999999",
            },
            "notify": {"email": True, "sms": True},
        }
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                "https://api.razorpay.com/v1/payment_links",
                json=payload,
                auth=self._auth(),
            )
            resp.raise_for_status()
            return resp.json()

    def fetch_payment(self, razorpay_payment_id: str) -> dict:
        if not self.enabled or not razorpay_payment_id:
            raise RuntimeError("Razorpay not enabled / no id")
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"https://api.razorpay.com/v1/payments/{razorpay_payment_id}",
                auth=self._auth(),
            )
            resp.raise_for_status()
            return resp.json()

    def create_order(self, amount: float, currency: str = "INR", receipt: str = "") -> dict:
        if not self.enabled:
            # Safe local test simulation
            order_id = f"order_sim_{hashlib.md5(f'{amount}{receipt}'.encode()).hexdigest()[:12]}"
            return {
                "id": order_id,
                "entity": "order",
                "amount": int(round(amount * 100)),
                "amount_paid": 0,
                "amount_due": int(round(amount * 100)),
                "currency": currency,
                "receipt": receipt,
                "status": "created",
                "attempts": 0,
            }
        payload = {
            "amount": int(round(amount * 100)),
            "currency": currency,
            "receipt": receipt or "rcpt_resurge",
        }
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                "https://api.razorpay.com/v1/orders",
                json=payload,
                auth=self._auth(),
            )
            resp.raise_for_status()
            return resp.json()

    def fetch_order(self, razorpay_order_id: str) -> dict:
        if not self.enabled or not razorpay_order_id:
            return {"id": razorpay_order_id, "status": "paid"}
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"https://api.razorpay.com/v1/orders/{razorpay_order_id}",
                auth=self._auth(),
            )
            resp.raise_for_status()
            return resp.json()

    # ---------- webhook verification & generation ----------
    def verify_webhook_signature(self, body: bytes, signature: str, timestamp: str | None = None) -> bool:
        """Verify Razorpay webhook signature (HMAC-SHA256)."""
        if not self.webhook_secret:
            # If no secret is configured, reject for security unless in dev mode
            return True if not settings.RAZORPAY_ENABLED else False
        expected = self.generate_webhook_signature(body, self.webhook_secret)
        return hmac.compare_digest(expected, signature or "")

    @staticmethod
    def generate_webhook_signature(body: bytes, secret: str) -> str:
        """Generate HMAC-SHA256 signature for Razorpay webhook testing."""
        return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


razorpay_client = RazorpayClient()

