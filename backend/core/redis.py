"""
Redis client management.
Provides singleton Redis client with async support.
"""
from typing import Optional

import redis.asyncio as aioredis
from redis.backoff import ExponentialBackoff
from redis.retry import Retry

from backend.core.config import settings

# Global Redis client instance
_redis_client: Optional[aioredis.Redis] = None


async def connect_redis() -> None:
    """
    Initialize Redis connection.
    Called during application startup.
    """
    global _redis_client
    # Enable automatic retries on timeouts and health checking
    retry_policy = Retry(ExponentialBackoff(cap=5, base=0.5), 3)
    _redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf8",
        decode_responses=True,
        retry_on_timeout=True,
        health_check_interval=30,
        socket_keepalive=True,
        retry=retry_policy,
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


async def get_redis() -> aioredis.Redis:
    """
    Dependency: Get Redis client instance.

    Returns:
        aioredis.Redis: Active Redis connection

    Raises:
        RuntimeError: If Redis is not initialized
    """
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized")
    return _redis_client
