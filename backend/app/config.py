"""Central application configuration loaded from environment variables.

All secrets and external integrations are configurable through environment
variables. Nothing sensitive is hardcoded.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # --- Core ---
    PROJECT_NAME: str = "RESURGE"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"

    # Local dev defaults to SQLite so the app runs without Docker/Postgres.
    # In docker-compose this is overridden to a Postgres URL.
    DATABASE_URL: str = "sqlite:///./resurge.db"

    # --- Security ---
    SECRET_KEY: str = "change-me-in-production-please-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # --- LLM (optional). If provider is "none" agents use deterministic heuristics. ---
    LLM_PROVIDER: Literal["none", "openai", "anthropic"] = "none"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = ""

    # --- Razorpay (Test Mode only) ---
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_ENABLED: bool = False  # When False, a safe local simulation is used.

    # --- MCP ---
    # Token the backend gateway uses to authorize tool calls to the MCP server.
    MCP_AUTH_TOKEN: str = "dev-mcp-token-change-me"
    # If True, the backend connects to an external MCP server over stdio.
    # If False, it uses the in-process tool layer (same validated code path).
    MCP_EXTERNAL: bool = False
    MCP_SERVER_COMMAND: str = "python"
    MCP_SERVER_ARGS: str = "-m app.mcp.server"

    # --- Rate limiting (best-effort in-memory) ---
    RATE_LIMIT_PER_MINUTE: int = 120

    # Merchant that ingests Razorpay webhooks (maps provider account -> tenant).
    WEBHOOK_MERCHANT_ID: int = 1

    # --- CORS ---
    CORS_ORIGINS: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
