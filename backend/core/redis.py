"""
Redis client management.
Provides singleton Redis client with async support.
"""
from typing import Optional

import redis.asyncio as redis

from backend.core.config import settings

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


async def connect_redis() -> None:
    """
    Initialize Redis connection.
    Called during application startup.
    """
    global _redis_client
    _redis_client = redis.from_url(
        settings.redis_url,
        encoding="utf8",
        decode_responses=True,
    )


async def close_redis() -> None:
    """
    Close Redis connection.
    Called during application shutdown.
    """
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


async def get_redis() -> redis.Redis:
    """
    Dependency: Get Redis client instance.

    Returns:
        redis.Redis: Active Redis connection

    Raises:
        RuntimeError: If Redis is not initialized
    """
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized")
    return _redis_client
