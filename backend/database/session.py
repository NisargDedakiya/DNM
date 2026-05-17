"""
SQLAlchemy async session management.
Provides database connection pool and session factory for async operations.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.config import settings

# Create async SQLAlchemy engine
# Uses asyncpg for PostgreSQL connections
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    connect_args={
        "timeout": 30,
    },
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency: Get database session.

    Yields:
        AsyncSession: Database session for use in route handlers

    Example:
        @router.get("/items")
        async def list_items(session: AsyncSession = Depends(get_db)):
            result = await session.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database schema.
    Creates all tables from models.
    """
    async with engine.begin() as conn:
        from backend.database.base import Base

        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.
    Called during application shutdown.
    """
    await engine.dispose()
