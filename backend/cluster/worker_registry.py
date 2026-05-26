"""
Worker registry for distributed scan cluster management.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.worker_node import WorkerNode


class WorkerRegistry:
    """Registers and tracks worker lifecycle state."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_worker(
        self,
        worker_id: UUID | None,
        region: str,
        capabilities: dict[str, Any] | None = None,
        organization_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkerNode:
        if worker_id:
            worker = await self.db.get(WorkerNode, worker_id)
        else:
            worker = None

        if worker is None:
            worker = WorkerNode(
                id=worker_id or uuid4(),
                region=region,
                status="idle",
                current_load=0,
                health_score=1.0,
                last_heartbeat=datetime.now(timezone.utc),
                organization_id=organization_id,
                capabilities=capabilities or {},
                metadata_=metadata or {},
            )
            self.db.add(worker)
        else:
            worker.region = region
            worker.status = "idle"
            worker.capabilities = capabilities or worker.capabilities or {}
            worker.organization_id = organization_id
            worker.metadata_ = metadata or worker.metadata_ or {}
            worker.last_heartbeat = datetime.now(timezone.utc)

        await self.db.flush()
        return worker

    async def deregister_worker(self, worker_id: UUID) -> None:
        worker = await self.db.get(WorkerNode, worker_id)
        if worker:
            worker.status = "offline"
            worker.current_load = 0
            worker.last_heartbeat = datetime.now(timezone.utc)
            await self.db.flush()

    async def update_worker_status(
        self,
        worker_id: UUID,
        status: str,
        current_load: int | None = None,
        health_score: float | None = None,
    ) -> WorkerNode | None:
        worker = await self.db.get(WorkerNode, worker_id)
        if not worker:
            return None

        worker.status = status
        if current_load is not None:
            worker.current_load = max(0, int(current_load))
        if health_score is not None:
            worker.health_score = max(0.0, min(1.0, float(health_score)))
        worker.last_heartbeat = datetime.now(timezone.utc)
        await self.db.flush()
        return worker

    async def get_available_workers(
        self,
        organization_id: str | None = None,
        region: str | None = None,
        min_health: float = 0.5,
        limit: int = 100,
    ) -> list[WorkerNode]:
        query = select(WorkerNode).where(
            WorkerNode.status.in_(["idle", "busy"]),
            WorkerNode.health_score >= min_health,
        )
        if organization_id:
            query = query.where(
                (WorkerNode.organization_id == organization_id) | (WorkerNode.organization_id.is_(None))
            )
        if region:
            query = query.where(WorkerNode.region == region)
        query = query.order_by(desc(WorkerNode.health_score), WorkerNode.current_load.asc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

