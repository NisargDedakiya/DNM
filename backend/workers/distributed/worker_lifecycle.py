"""
Worker lifecycle control for startup, shutdown, and restart.
"""
from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.events import EventType
from backend.services.event_service import event_service
from backend.cluster.worker_registry import WorkerRegistry


class WorkerLifecycle:
    """Coordinates worker lifecycle transitions and heartbeat handling."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = WorkerRegistry(db)
        self._heartbeat_task: asyncio.Task | None = None

    async def start_worker(self, worker_id: UUID | None, region: str, capabilities: dict[str, Any] | None = None) -> dict[str, Any]:
        worker = await self.registry.register_worker(worker_id, region, capabilities=capabilities)
        return {"worker_id": str(worker.id), "status": worker.status, "region": worker.region}

    async def stop_worker(self, worker_id: UUID) -> None:
        await self.registry.deregister_worker(worker_id)
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

    async def restart_worker(self, worker_id: UUID, region: str, capabilities: dict[str, Any] | None = None) -> dict[str, Any]:
        await self.stop_worker(worker_id)
        return await self.start_worker(worker_id, region, capabilities=capabilities)

    async def heartbeat(self, worker_id: UUID, current_load: int, health_score: float) -> None:
        worker = await self.registry.update_worker_status(worker_id, "busy" if current_load else "idle", current_load=current_load, health_score=health_score)
        if worker:
            await event_service.emit_event(
                EventType.CLUSTER_WORKER_HEARTBEAT,
                str(worker.organization_id or "system"),
                {
                    "worker_id": str(worker.id),
                    "region": worker.region,
                    "current_load": worker.current_load,
                    "health_score": worker.health_score,
                },
            )

