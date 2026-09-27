"""Async SQLAlchemy engine, declarative base, and session lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import Settings, get_settings


class Base(DeclarativeBase):
    """Base class for infrastructure ORM models."""


def _async_database_url(settings: Settings) -> str:
    if settings.database_url is None or not settings.database_url.get_secret_value():
        raise RuntimeError("DATABASE_URL is required to create a database engine")
    value = settings.database_url.get_secret_value()
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql+psycopg://"):
        return value
    raise RuntimeError("DATABASE_URL must use the postgresql:// scheme")


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create an async engine without opening a database connection."""

    configured = settings or get_settings()
    return create_async_engine(
        _async_database_url(configured),
        echo=configured.database_echo,
        pool_size=configured.database_pool_size,
        max_overflow=configured.database_max_overflow,
        pool_timeout=configured.database_pool_timeout_seconds,
    )


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the process engine singleton."""

    return create_engine()


def get_session_factory(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Create a session factory bound to the supplied or process engine."""

    return async_sessionmaker(engine or get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session and roll back unhandled failures."""

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
