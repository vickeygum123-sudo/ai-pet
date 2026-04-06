"""Database helpers for the backend foundation persistence layer."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Declarative SQLAlchemy base."""


DEFAULT_DATABASE_URL = "sqlite:///./backend_foundation.db"


def get_database_url() -> str:
    """Resolve the configured database URL with a SQLite local-dev fallback."""
    return os.getenv("BACKEND_DATABASE_URL", DEFAULT_DATABASE_URL)


def create_engine_from_url(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for PostgreSQL or local SQLite."""
    url = database_url or get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, connect_args=connect_args)


def create_session_factory(database_url: str | None = None) -> sessionmaker:
    """Create a session factory bound to the configured engine."""
    engine = create_engine_from_url(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
