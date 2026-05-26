"""
Org-isolated cache helpers with Redis backing and in-memory fallback.
"""
from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from copy import deepcopy
from typing import Any

from backend.core.redis import get_redis

_LOCAL_CACHE: dict[str, tuple[float, Any]] = {}
_LOCK = asyncio.Lock()


def _cache_key(organization_id: str, namespace: str, key: str) -> str:
    return f"performance:{organization_id}:{namespace}:{key}"


async def cache_result(
    organization_id: str,
    namespace: str,
    key: str,
    value: Any,
    ttl_seconds: int = 300,
) -> dict[str, Any]:
    cache_key = _cache_key(str(organization_id), namespace, key)
    payload = json.dumps(value, default=str)
    expires_at = time.time() + max(1, int(ttl_seconds))

    try:
        redis_client = await get_redis()
        await redis_client.set(cache_key, payload, ex=max(1, int(ttl_seconds)))
        backend = "redis"
    except Exception:
        async with _LOCK:
            _LOCAL_CACHE[cache_key] = (expires_at, deepcopy(value))
        backend = "memory"

    return {
        "cache_key": cache_key,
        "backend": backend,
        "ttl_seconds": int(ttl_seconds),
        "stored_at": time.time(),
    }


async def retrieve_cache(organization_id: str, namespace: str, key: str) -> Any | None:
    cache_key = _cache_key(str(organization_id), namespace, key)

    try:
        redis_client = await get_redis()
        raw = await redis_client.get(cache_key)
        if raw is None:
            raise KeyError(cache_key)
        return json.loads(raw)
    except Exception:
        async with _LOCK:
            cached = _LOCAL_CACHE.get(cache_key)
            if not cached:
                return None
            expires_at, value = cached
            if time.time() >= expires_at:
                _LOCAL_CACHE.pop(cache_key, None)
                return None
            return deepcopy(value)


async def invalidate_cache(organization_id: str, namespace: str, key: str | None = None) -> dict[str, Any]:
    prefix = _cache_key(str(organization_id), namespace, "")

    try:
        redis_client = await get_redis()
        keys = [prefix + key] if key else [candidate async for candidate in redis_client.scan_iter(match=f"{prefix}*")]
        deleted = 0
        for cache_key in keys:
            deleted += int(await redis_client.delete(cache_key))
        backend = "redis"
    except Exception:
        async with _LOCK:
            if key:
                deleted = 1 if _LOCAL_CACHE.pop(prefix + key, None) else 0
            else:
                matched = [cache_key for cache_key in list(_LOCAL_CACHE) if cache_key.startswith(prefix)]
                deleted = len(matched)
                for cache_key in matched:
                    _LOCAL_CACHE.pop(cache_key, None)
        backend = "memory"

    return {"backend": backend, "deleted": deleted, "organization_id": str(organization_id), "namespace": namespace}
