"""Reusable common API schemas."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class HealthResponse(BaseModel):
    status: str
    version: str
    ml_model_loaded: bool
    razorpay_enabled: bool


class Pagination(BaseModel):
    page: int = 1
    page_size: int = 25
    total: int = 0


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
