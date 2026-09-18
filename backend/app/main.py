"""FastAPI application entrypoint.

Wires together routers, CORS, security, the configurable model store and the
MCP gateway. On startup it ensures the ML model is loaded (training if needed).
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.logging_setup import logger
from app.routers import (
    agents,
    analytics,
    audit,
    auth,
    cases,
    command,
    customers,
    dashboard,
    demo,
    mcp,
    ml,
    payments,
    root,
    settings as settings_router,
    webhooks,
)
from app.services.ml_pipeline import ensure_model

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Autonomous AI Revenue Recovery Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Best-effort in-memory rate limiting ---
_RATE = defaultdict(list)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path.endswith(("/login", "/register", "/demo/run")):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = _RATE[ip]
        window[:] = [t for t in window if now - t < 60]
        if len(window) >= settings.RATE_LIMIT_PER_MINUTE:
            return JSONResponse(status_code=429, content={"detail": "rate limited"})
        window.append(now)
    return await call_next(request)


for r in (
    auth.router,
    root.router,
    dashboard.router,
    cases.router,
    customers.router,
    payments.router,
    audit.router,
    agents.router,
    analytics.router,
    command.router,
    ml.router,
    mcp.router,
    settings_router.router,
    demo.router,
    webhooks.router,
):
    app.include_router(r, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
def _startup() -> None:
    logger.info("RECOVERAI backend starting up (env=%s)", settings.ENVIRONMENT)
    try:
        ensure_model()
        logger.info("ML model ready: %s", "loaded" if True else "trained")
    except Exception as e:  # pragma: no cover
        logger.warning("Model load deferred: %s", e)


@app.get("/")
def index() -> dict:
    return {"name": settings.PROJECT_NAME, "docs": "/docs", "health": "/health"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    from app.services.ml_pipeline import model_store
    db_status = "ok"
    try:
        db.execute(select(1)).scalar()
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": settings.PROJECT_NAME,
        "database": db_status,
        "ml_model_loaded": model_store.is_loaded(),
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
