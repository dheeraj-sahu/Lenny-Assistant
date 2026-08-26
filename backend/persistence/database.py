"""
persistence/database.py

Async SQLAlchemy engine and session factory.
The engine is created once at application startup and reused for the lifetime
of the process. Each request gets its own AsyncSession via get_db().
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.logging import get_logger

logger = get_logger(__name__)

# Module-level singletons — populated by init_db()
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str) -> None:
    """
    Create the async engine and session factory.
    Call this once during application startup (lifespan in main.py).
    """
    global _engine, _session_factory

    _engine = create_async_engine(
        database_url,
        echo=False,           # set to True to log all SQL (noisy in prod)
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,   # test connections before handing them out
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        expire_on_commit=False,
        autoflush=False,
    )
    logger.info("database_initialized", url=database_url.split("@")[-1])  # log host only


async def close_db() -> None:
    """Dispose the engine. Call during application shutdown."""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("database_disposed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields one AsyncSession per request.
    Usage:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    if _session_factory is None:
        raise RuntimeError("Database has not been initialized. Call init_db() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_engine() -> AsyncEngine:
    """Return the engine (used by Alembic and health checks)."""
    if _engine is None:
        raise RuntimeError("Database has not been initialized. Call init_db() first.")
    return _engine
