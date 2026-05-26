"""
Cluster state orchestration and task assignment.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cluster.load_balancer import LoadBalancer
from backend.cluster.worker_registry import WorkerRegistry
from backend.models.cluster_job import ClusterJob


class ClusterManager:
    """Orchestrates worker assignment, rebalancing, and task recovery."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = WorkerRegistry(db)
        self.load_balancer = LoadBalancer()

    async def assign_cluster_job(
        self,
        job: ClusterJob,
        required_capabilities: list[str] | None = None,
    ) -> dict[str, Any]:
        workers = await self.registry.get_available_workers(str(job.organization_id), limit=200)
        worker = self.load_balancer.select_worker(workers, required_capabilities=required_capabilities)
        if not worker:
            return {"assigned": False, "reason": "no_available_workers"}

        job.assigned_worker = worker.id
        job.status = "assigned"
        worker.status = "busy"
        worker.current_load = int(worker.current_load or 0) + 1
        await self.db.flush()
        return {"assigned": True, "worker_id": str(worker.id), "job_id": str(job.id)}

    async def rebalance_workers(self, organization_id: UUID | str) -> dict[str, Any]:
        org_id = str(organization_id)
        workers = await self.registry.get_available_workers(org_id, limit=500)
        overloaded = [worker for worker in workers if (worker.current_load or 0) > 10]
        reassigned = 0
        for worker in overloaded:
            worker.current_load = max(0, int(worker.current_load or 0) - 1)
            reassigned += 1
        await self.db.flush()
        return {
            "organization_id": org_id,
            "workers_seen": len(workers),
            "rebalanced_workers": reassigned,
        }

    async def recover_failed_tasks(self, organization_id: UUID | str, limit: int = 20) -> dict[str, Any]:
        org_id = str(organization_id)
        query = (
            select(ClusterJob)
            .where(ClusterJob.organization_id == org_id, ClusterJob.status == "failed")
            .order_by(ClusterJob.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        jobs = result.scalars().all()
        recovered = 0
        for job in jobs:
            job.status = "queued"
            job.attempts = int(job.attempts or 0) + 1
            recovered += 1
        await self.db.flush()
        return {
            "organization_id": org_id,
            "failed_jobs": len(jobs),
            "recovered_jobs": recovered,
        }

