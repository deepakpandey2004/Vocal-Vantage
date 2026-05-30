"""Async SQLAlchemy database setup.

We use the async engine so the API stays non-blocking. PostgreSQL is the
target in production (via asyncpg); SQLite is the zero-config default for
local development so the project runs out of the box.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _normalise_db_url(url: str) -> str:
    """Make common Postgres URLs async-compatible.

    Render / Heroku hand out URLs like ``postgres://...`` — SQLAlchemy needs
    the explicit ``postgresql+asyncpg://`` driver prefix.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


DATABASE_URL = _normalise_db_url(settings.database_url)

# SQLite needs a special connect arg; Postgres does not.
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # set to True only when debugging SQL; very verbose otherwise
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a scoped async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create tables on startup (simple projects); use Alembic for real migrations."""
    # Import models so they are registered on the metadata before create_all.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
