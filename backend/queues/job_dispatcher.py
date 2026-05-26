"""
Cluster job dispatcher coordinating queueing and worker assignment.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.cluster.cluster_manager import ClusterManager
from backend.models.cluster_job import ClusterJob
from backend.queues.priority_queue import PriorityQueue


class JobDispatcher:
    """Dispatches jobs into the cluster with severity-aware prioritization."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.priority_queue = PriorityQueue()
        self.cluster_manager = ClusterManager(db)

    def prioritize_job(self, task_type: str, priority: str | None = None, severity: str | None = None) -> str:
        if priority:
            return priority
        severity = (severity or "medium").lower()
        if severity in {"critical", "high", "medium", "low"}:
            return severity
        if task_type in {"nuclei", "dalfox", "ffuf"}:
            return "high"
        return "medium"

    async def dispatch_job(
        self,
        organization_id: UUID,
        task_type: str,
        payload: dict[str, Any],
        priority: str | None = None,
    ) -> ClusterJob:
        job_priority = self.prioritize_job(task_type, priority, payload.get("severity"))
        job = ClusterJob(
            organization_id=organization_id,
            task_type=task_type,
            priority=job_priority,
            status="queued",
            payload=payload,
        )
        self.db.add(job)
        await self.db.flush()

        queue_payload = {
            "job_id": str(job.id),
            "organization_id": str(organization_id),
            "task_type": task_type,
            "payload": payload,
            "priority": job_priority,
        }
        await self.priority_queue.enqueue(str(organization_id), queue_payload, priority=job_priority)
        return job

    async def retry_failed_job(self, job_id: UUID) -> ClusterJob | None:
        job = await self.db.get(ClusterJob, job_id)
        if not job:
            return None
        job.status = "queued"
        job.attempts = int(job.attempts or 0) + 1
        await self.db.flush()
        await self.priority_queue.retry(str(job.organization_id), str(job.id), priority=job.priority)
        return job

