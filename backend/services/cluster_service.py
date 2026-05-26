"""
Service layer for distributed cluster orchestration.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.cluster.cluster_manager import ClusterManager
from backend.cluster.worker_registry import WorkerRegistry
from backend.core.events import EventType
from backend.models.cluster_job import ClusterJob
from backend.queues.job_dispatcher import JobDispatcher
from backend.services.event_service import event_service


class ClusterService:
    """Coordinates distributed execution, monitoring, and recovery."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dispatcher = JobDispatcher(db)
        self.cluster_manager = ClusterManager(db)
        self.worker_registry = WorkerRegistry(db)

    async def execute_distributed_scan(
        self,
        organization_id: UUID,
        task_type: str,
        payload: dict[str, Any],
        priority: str | None = None,
    ) -> dict[str, Any]:
        job = await self.dispatcher.dispatch_job(organization_id, task_type, payload, priority=priority)
        assignment = await self.cluster_manager.assign_cluster_job(job, required_capabilities=payload.get("capabilities"))
        await event_service.emit_event(EventType.CLUSTER_JOB_QUEUED, str(organization_id), {"job_id": str(job.id), "task_type": task_type, "assignment": assignment})
        if assignment.get("assigned"):
            await event_service.emit_event(EventType.CLUSTER_JOB_ASSIGNED, str(organization_id), {"job_id": str(job.id), "worker_id": assignment.get("worker_id")})
        return {"job_id": str(job.id), "status": job.status, "assignment": assignment}

    async def monitor_cluster_execution(self, organization_id: UUID) -> dict[str, Any]:
        org_id = str(organization_id)
        workers = await self.worker_registry.get_available_workers(org_id, limit=500)
        jobs = await self._get_jobs(org_id)
        busy = sum(1 for worker in workers if (worker.current_load or 0) > 0)
        return {
            "organization_id": str(organization_id),
            "worker_count": len(workers),
            "busy_workers": busy,
            "job_count": len(jobs),
            "jobs": jobs,
        }

    async def recover_failed_execution(self, organization_id: UUID) -> dict[str, Any]:
        return await self.cluster_manager.recover_failed_tasks(organization_id)

    async def _get_jobs(self, organization_id: str) -> list[dict[str, Any]]:
        from sqlalchemy import select

        query = select(ClusterJob).where(ClusterJob.organization_id == organization_id).order_by(ClusterJob.created_at.desc()).limit(50)
        result = await self.db.execute(query)
        jobs = result.scalars().all()
        return [
            {
                "id": str(job.id),
                "task_type": job.task_type,
                "priority": job.priority,
                "status": job.status,
                "assigned_worker": str(job.assigned_worker) if job.assigned_worker else None,
                "created_at": job.created_at.isoformat(),
            }
            for job in jobs
        ]

