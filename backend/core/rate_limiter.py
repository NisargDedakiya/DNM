"""
Redis-backed async rate limiter for scans.

Provides per-user quota checks and simple concurrency slots per program.
"""
from __future__ import annotations

from typing import Optional

from backend.core.redis import get_redis


async def check_scan_limit(user_id: str, limit: int, window_seconds: int) -> bool:
    """Return True if user is allowed to start a scan (under the limit).

    This does NOT increment the counter; call increment_scan_counter after allowing.
    """
    r = await get_redis()
    key = f"rate:scans:{user_id}"
    val = await r.get(key)
    if val is None:
        return True
    try:
        return int(val) < int(limit)
    except Exception:
        return True


async def increment_scan_counter(user_id: str, window_seconds: int) -> int:
    """Increment user's scan counter and set TTL on first increment.

    Returns the new counter value.
    """
    r = await get_redis()
    key = f"rate:scans:{user_id}"
    # Use a transaction to set expiry only when key is created
    new = await r.incr(key)
    if new == 1:
        await r.expire(key, window_seconds)
    return int(new)


async def reset_limits(user_id: Optional[str] = None) -> None:
    r = await get_redis()
    if user_id:
        await r.delete(f"rate:scans:{user_id}")
    else:
        # WARNING: deletes all rate keys -- use with care
        keys = await r.keys("rate:scans:*")
        if keys:
            await r.delete(*keys)


async def acquire_concurrency_slot(program_id: str, max_slots: int) -> bool:
    """Try to acquire a concurrency slot for program_id. Returns True if acquired."""
    r = await get_redis()
    key = f"concurrent:program:{program_id}"
    # increment and check
    val = await r.incr(key)
    if val == 1:
        # set a generous TTL so leaked slots don't remain forever
        await r.expire(key, 60 * 60)
    if val > max_slots:
        # revert
        await r.decr(key)
        return False
    return True


async def release_concurrency_slot(program_id: str) -> None:
    r = await get_redis()
    key = f"concurrent:program:{program_id}"
    val = await r.decr(key)
    # prevent negative
    if val is None or int(val) < 0:
        await r.set(key, 0)
