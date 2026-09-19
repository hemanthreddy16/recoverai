"""Bills, EMIs, recurring financial obligations models with AI risk prediction and Smart Reminder Engine."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BillEmi(Base):
    """Recurring or scheduled financial obligation (e.g. Utility bill, EMI, Rent, Subscription)."""

    __tablename__ = "bills_emis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Category: Electricity | Internet | Mobile | Rent | EMI | Insurance | Subscription | Other
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    # Recurrence: One-time | Weekly | Monthly | Quarterly | Yearly
    recurrence: Mapped[str] = mapped_column(String(40), default="Monthly")

    customer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    payment_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status: Upcoming | Due Today | Overdue | Paid | Failed
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Upcoming", index=True)
    
    # AI Risk Assessment fields (0-100 score, Low/Medium/High level, explanation reason)
    risk_score: Mapped[int] = mapped_column(Integer, default=15, index=True)  # 0 to 100
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="Low", index=True)  # Low | Medium | High
    risk_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_factors: Mapped[str | None] = mapped_column(Text, default="[]")  # JSON list of factor strings
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime, default=_utcnow)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationship to reminder logs
    reminder_logs: Mapped[list["BillReminderLog"]] = relationship(
        "BillReminderLog",
        back_populates="bill",
        cascade="all, delete-orphan",
        order_by="desc(BillReminderLog.sent_at)",
    )

    # Relationship to risk calculation history
    risk_history: Mapped[list["BillRiskHistory"]] = relationship(
        "BillRiskHistory",
        back_populates="bill",
        cascade="all, delete-orphan",
        order_by="desc(BillRiskHistory.evaluated_at)",
    )

    def set_risk_factors(self, factors: list[str]) -> None:
        self.risk_factors = json.dumps(factors or [])

    def get_risk_factors(self) -> list[str]:
        try:
            return json.loads(self.risk_factors or "[]")
        except json.JSONDecodeError:
            return []


class BillReminderLog(Base):
    """WhatsApp, Email, or SMS communication reminder sent for a specific bill/EMI with delivery and response tracking."""

    __tablename__ = "bill_reminder_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bill_id: Mapped[int] = mapped_column(
        ForeignKey("bills_emis.id", ondelete="CASCADE"), nullable=False, index=True
    )
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # stage: 7-day | 3-day | 1-day | due_today | overdue | recovery | manual
    stage: Mapped[str] = mapped_column(String(40), default="normal", index=True)
    channel: Mapped[str] = mapped_column(String(30), default="whatsapp")
    recipient_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # status / delivery_status: scheduled | sent | delivered | opened | failed
    status: Mapped[str] = mapped_column(String(30), default="delivered")
    delivery_status: Mapped[str] = mapped_column(String(30), default="delivered")
    
    # customer_response: pending | opened_link | responded | paid
    customer_response: Mapped[str] = mapped_column(String(40), default="pending")
    
    # payment_status_after: pending | settled | overdue
    payment_status_after: Mapped[str] = mapped_column(String(30), default="pending")
    
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    bill: Mapped["BillEmi"] = relationship("BillEmi", back_populates="reminder_logs")


class BillRiskHistory(Base):
    """Time-series record of AI risk score predictions and contributing factors for a bill/EMI."""

    __tablename__ = "bill_risk_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bill_id: Mapped[int] = mapped_column(
        ForeignKey("bills_emis.id", ondelete="CASCADE"), nullable=False, index=True
    )
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 to 100
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)  # Low | Medium | High
    risk_reason: Mapped[str | None] = mapped_column(String(255))
    factors: Mapped[str | None] = mapped_column(Text, default="[]")  # JSON string
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    bill: Mapped["BillEmi"] = relationship("BillEmi", back_populates="risk_history")

    def set_factors(self, factor_list: list[str]) -> None:
        self.factors = json.dumps(factor_list or [])

    def get_factors(self) -> list[str]:
        try:
            return json.loads(self.factors or "[]")
        except json.JSONDecodeError:
            return []


class BillReminderSettings(Base):
    """Configurable reminder preferences, quiet hours, and AI risk multipliers per merchant."""

    __tablename__ = "bill_reminder_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # frequency: smart | conservative | aggressive | daily
    frequency: Mapped[str] = mapped_column(String(30), default="smart")
    max_reminders: Mapped[int] = mapped_column(Integer, default=4)
    # preferred_channel: whatsapp | email | sms | multi
    preferred_channel: Mapped[str] = mapped_column(String(30), default="whatsapp")
    
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    quiet_hours_start: Mapped[str] = mapped_column(String(10), default="22:00")  # "HH:MM" 24h
    quiet_hours_end: Mapped[str] = mapped_column(String(10), default="08:00")    # "HH:MM" 24h
    
    risk_multiplier_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
