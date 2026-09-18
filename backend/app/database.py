"""SQLAlchemy engine, session factory and declarative base.

The database backend is configurable through DATABASE_URL so the project runs
against SQLite locally and PostgreSQL inside Docker without code changes.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = settings.DATABASE_URL
    connect_args = {}
    # SQLite needs check_same_thread=False for use across FastAPI threads.
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    # Import models so they are registered on Base before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
