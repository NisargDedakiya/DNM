"""
Redis-backed distributed lock manager for coordinating distributed worker tasks.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Optional
from redis.asyncio import Redis

from backend.core.redis import get_redis

logger = logging.getLogger(__name__)

# Lua script to release the lock atomically only if the token matches.
# Avoids releasing a lock that has been acquired by another worker after a timeout.
RELEASE_LUA_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

class RedisLock:
    """
    Async distributed lock using Redis.
    Supports context manager pattern (async with).
    """

    def __init__(self, key: str, ttl_seconds: int = 60) -> None:
        self.key = f"lock:{key}"
        self.ttl = ttl_seconds
        self.token = str(uuid.uuid4())
        self.redis: Optional[Redis] = None

    async def acquire(self, blocking: bool = True, timeout: float | None = None) -> bool:
        """
        Acquire the distributed lock.

        Parameters
        ----------
        blocking :
            If True, blocks until lock is available.
        timeout :
            Maximum blocking wait time in seconds.

        Returns
        -------
        bool: True if lock acquired, False otherwise.
        """
        self.redis = await get_redis()
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Set key only if not exists (nx) with a millisecond expiry time (px)
            acquired = await self.redis.set(self.key, self.token, px=self.ttl * 1000, nx=True)
            if acquired:
                logger.debug(f"Acquired distributed lock: {self.key} with token {self.token}")
                return True

            if not blocking:
                return False

            # Check timeout limit
            if timeout is not None and (asyncio.get_event_loop().time() - start_time) >= timeout:
                logger.warning(f"Timeout reached while acquiring distributed lock: {self.key}")
                return False

            # Exponential backoff delay with jitter
            await asyncio.sleep(0.2)

    async def release(self) -> None:
        """
        Release the distributed lock atomically.
        """
        if not self.redis:
            self.redis = await get_redis()

        try:
            # Run Lua script to delete key only if token matches
            released = await self.redis.eval(RELEASE_LUA_SCRIPT, 1, self.key, self.token)
            if released:
                logger.debug(f"Released distributed lock: {self.key} (token matched)")
            else:
                logger.warning(f"Attempted to release lock {self.key} but token did not match or lock expired")
        except Exception as e:
            logger.error(f"Error releasing distributed lock {self.key}: {e}")

    async def __aenter__(self) -> RedisLock:
        acquired = await self.acquire(blocking=True)
        if not acquired:
            raise RuntimeError(f"Could not acquire distributed lock: {self.key}")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.release()
