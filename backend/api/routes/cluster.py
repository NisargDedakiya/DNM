"""
Cluster API routes for distributed execution and worker health.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.core.permissions import Permission, RBACService
from backend.database.session import get_db
from backend.models.user import User
from backend.services.cluster_service import ClusterService
from backend.health.cluster_monitor import ClusterMonitor
from backend.cluster.worker_registry import WorkerRegistry

router = APIRouter(prefix="/cluster", tags=["cluster"])


async def get_cluster_service(db: AsyncSession = Depends(get_db)) -> ClusterService:
    return ClusterService(db)


async def get_rbac(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def get_worker_registry(db: AsyncSession = Depends(get_db)) -> WorkerRegistry:
    return WorkerRegistry(db)


async def _require_workspace(user_id: UUID, organization_id: UUID, rbac: RBACService) -> None:
    await rbac.validate_workspace_access(user_id, organization_id)


@router.get("/workers", summary="List cluster workers")
async def list_workers(
    organization_id: UUID = Query(...),
    region: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    registry: WorkerRegistry = Depends(get_worker_registry),
    rbac: RBACService = Depends(get_rbac),
) -> list[dict[str, Any]]:
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    workers = await registry.get_available_workers(str(organization_id), region=region, limit=200)
    return [
        {
            "id": str(worker.id),
            "region": worker.region,
            "status": worker.status,
            "current_load": worker.current_load,
            "health_score": round(float(worker.health_score or 0.0), 3),
            "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
            "capabilities": worker.capabilities or {},
        }
        for worker in workers
    ]


@router.get("/jobs", summary="List cluster jobs")
async def list_jobs(
    organization_id: UUID = Query(...),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    cluster_service: ClusterService = Depends(get_cluster_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    data = await cluster_service.monitor_cluster_execution(organization_id)
    jobs = data.get("jobs", [])
    if status:
        jobs = [job for job in jobs if job.get("status") == status]
    data["jobs"] = jobs
    return data


@router.get("/health", summary="Cluster health overview")
async def cluster_health(
    organization_id: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    registry: WorkerRegistry = Depends(get_worker_registry),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    workers = await registry.get_available_workers(str(organization_id), limit=500)
    monitor = ClusterMonitor()
    return {
        "organization_id": str(organization_id),
        **await monitor.monitor_cluster(workers),
        "issues": monitor.detect_cluster_issues(workers),
    }


@router.post("/rebalance", summary="Rebalance cluster workers")
async def rebalance_cluster(
    organization_id: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    cluster_service: ClusterService = Depends(get_cluster_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    return await cluster_service.cluster_manager.rebalance_workers(organization_id)

