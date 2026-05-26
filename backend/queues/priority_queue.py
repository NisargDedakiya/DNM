"""
Redis-backed priority queue for cluster jobs.
"""
from __future__ import annotations

import json
import time
from typing import Any
from uuid import uuid4

from backend.core.redis import get_redis


PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class PriorityQueue:
    """Stores and retrieves cluster jobs by severity-aware priority."""

    def __init__(self, namespace: str = "cluster_jobs"):
        self.namespace = namespace

    def _queue_key(self, organization_id: str) -> str:
        return f"{self.namespace}:{organization_id}"

    def _job_key(self, job_id: str) -> str:
        return f"{self.namespace}:job:{job_id}"

    def _score(self, priority: str) -> float:
        return float(PRIORITY_RANK.get(priority, PRIORITY_RANK["medium"]))

    async def enqueue(self, organization_id: str, job_data: dict[str, Any], priority: str = "medium") -> str:
        redis_client = await get_redis()
        job_id = str(job_data.get("job_id") or uuid4())
        payload = {
            **job_data,
            "job_id": job_id,
            "organization_id": organization_id,
            "priority": priority,
            "status": job_data.get("status", "queued"),
            "queued_at": time.time(),
        }
        await redis_client.set(self._job_key(job_id), json.dumps(payload, default=str))
        score = self._score(priority) * 1_000_000_000 + time.time()
        await redis_client.zadd(self._queue_key(organization_id), {job_id: score})
        return job_id

    async def dequeue(self, organization_id: str) -> dict[str, Any] | None:
        redis_client = await get_redis()
        result = await redis_client.zpopmin(self._queue_key(organization_id), count=1)
        if not result:
            return None
        job_id = result[0][0]
        raw = await redis_client.get(self._job_key(job_id))
        if not raw:
            return None
        return json.loads(raw)

    async def retry(self, organization_id: str, job_id: str, priority: str | None = None) -> dict[str, Any] | None:
        redis_client = await get_redis()
        raw = await redis_client.get(self._job_key(job_id))
        if not raw:
            return None
        job = json.loads(raw)
        job["attempts"] = int(job.get("attempts", 0)) + 1
        job["status"] = "queued"
        if priority:
            job["priority"] = priority
        await redis_client.set(self._job_key(job_id), json.dumps(job, default=str))
        score = self._score(job.get("priority", "medium")) * 1_000_000_000 + time.time()
        await redis_client.zadd(self._queue_key(organization_id), {job_id: score})
        return job

    async def length(self, organization_id: str) -> int:
        redis_client = await get_redis()
        return int(await redis_client.zcard(self._queue_key(organization_id)))

