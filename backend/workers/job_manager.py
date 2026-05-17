"""
Job manager using Redis to track job metadata and cancellations.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from backend.core.redis import get_redis


JOB_PREFIX = "job:"


async def _key(job_id: str) -> str:
    return f"{JOB_PREFIX}{job_id}"


async def create_job(job_type: str, user_id: str, meta: Dict[str, Any] | None = None) -> str:
    """Create job record in Redis and return job_id."""
    r = await get_redis()
    job_id = str(uuid4())
    payload = {
        "id": job_id,
        "type": job_type,
        "user_id": str(user_id),
        "status": "queued",
        "meta": json.dumps(meta or {}),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "cancelled": "0",
    }
    await r.hset(await _key(job_id), mapping=payload)
    return job_id


async def update_job_status(job_id: str, status: str, meta: Dict[str, Any] | None = None) -> None:
    r = await get_redis()
    key = await _key(job_id)
    data = {"status": status, "updated_at": datetime.utcnow().isoformat()}
    if meta is not None:
        data["meta"] = json.dumps(meta)
    await r.hset(key, mapping=data)


async def cancel_job(job_id: str) -> None:
    r = await get_redis()
    key = await _key(job_id)
    await r.hset(key, mapping={"cancelled": "1", "status": "cancelled", "updated_at": datetime.utcnow().isoformat()})


async def is_cancelled(job_id: str) -> bool:
    r = await get_redis()
    key = await _key(job_id)
    val = await r.hget(key, "cancelled")
    return val == "1"


async def get_job_status(job_id: str) -> Dict[str, Any] | None:
    r = await get_redis()
    key = await _key(job_id)
    data = await r.hgetall(key)
    if not data:
        return None
    # parse meta
    if data.get("meta"):
        try:
            data["meta"] = json.loads(data["meta"])
        except Exception:
            data["meta"] = {}
    return data
