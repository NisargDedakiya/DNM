"""
Grid API Routes.
Provides routes to inspect active grid agents, exposure mutations, anomaly events, and status summaries.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.core.permissions import Permission
from backend.services.rbac_service import RBACService
from backend.models.grid_agent import GridAgent
from backend.models.exposure_mutation import ExposureMutation
from backend.models.anomaly_event import AnomalyEvent
from backend.services.grid_service import GridService

router = APIRouter(prefix="/grid", tags=["grid"])


async def get_rbac(db: AsyncSession = Depends(get_db)) -> RBACService:
    """Dependency helper to load RBACService."""
    return RBACService(db)


async def enforce_grid_access(
    user_id: UUID,
    organization_id: UUID,
    rbac: RBACService,
) -> None:
    """Helper to enforce tenant isolation and asset visibility permissions."""
    await rbac.validate_workspace_access(user_id, organization_id)
    await rbac.check_permission(user_id, organization_id, Permission.VIEW_ASSETS)


# =============================================================================
# GRID AGENTS ROUTE
# =============================================================================

@router.get(
    "/agents",
    summary="List active grid monitoring agents",
    description="Fetch registered continuous monitoring agents for the organization workspace.",
)
async def list_grid_agents(
    organization_id: UUID = Query(..., description="Organization workspace ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac),
) -> list[dict[str, Any]]:
    """List agents."""
    await enforce_grid_access(current_user.id, organization_id, rbac)

    stmt = select(GridAgent).where(
        GridAgent.organization_id == organization_id
    ).order_by(GridAgent.last_heartbeat.desc())
    
    res = await db.execute(stmt)
    agents = res.scalars().all()

    return [
        {
            "id": str(agent.id),
            "status": agent.status,
            "monitored_assets_count": len(agent.monitored_assets.get("asset_ids", [])),
            "monitored_assets": agent.monitored_assets.get("asset_ids", []),
            "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
        }
        for agent in agents
    ]


# =============================================================================
# EXPOSURE MUTATIONS ROUTE
# =============================================================================

@router.get(
    "/mutations",
    summary="List asset exposure mutations",
    description="Fetch a timeline of mutations detected across monitored assets.",
)
async def list_exposure_mutations(
    organization_id: UUID = Query(..., description="Organization workspace ID"),
    severity: str | None = Query(None, description="Filter by severity: critical, high, medium, low, info"),
    mutation_type: str | None = Query(None, description="Filter by mutation type: dns_drift, cloud_exposure, auth_mutation"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac),
) -> list[dict[str, Any]]:
    """List mutations."""
    await enforce_grid_access(current_user.id, organization_id, rbac)

    stmt = select(ExposureMutation).where(
        ExposureMutation.organization_id == organization_id
    )

    if severity:
        stmt = stmt.where(ExposureMutation.severity == severity)
    if mutation_type:
        stmt = stmt.where(ExposureMutation.mutation_type == mutation_type)

    stmt = stmt.order_by(desc(ExposureMutation.created_at)).limit(limit)
    res = await db.execute(stmt)
    mutations = res.scalars().all()

    return [
        {
            "id": str(m.id),
            "asset": m.asset,
            "mutation_type": m.mutation_type,
            "severity": m.severity,
            "summary": m.summary,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in mutations
    ]


# =============================================================================
# ANOMALY EVENTS ROUTE
# =============================================================================

@router.get(
    "/anomalies",
    summary="List posture anomaly events",
    description="Fetch anomaly events detected in asset patterns or risk spikes.",
)
async def list_anomaly_events(
    organization_id: UUID = Query(..., description="Organization workspace ID"),
    severity: str | None = Query(None, description="Filter by severity: critical, high, medium, low"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac),
) -> list[dict[str, Any]]:
    """List anomalies."""
    await enforce_grid_access(current_user.id, organization_id, rbac)

    stmt = select(AnomalyEvent).where(
        AnomalyEvent.organization_id == organization_id
    )

    if severity:
        stmt = stmt.where(AnomalyEvent.severity == severity)

    stmt = stmt.order_by(desc(AnomalyEvent.detected_at)).limit(limit)
    res = await db.execute(stmt)
    anomalies = res.scalars().all()

    return [
        {
            "id": str(a.id),
            "anomaly_type": a.anomaly_type,
            "severity": a.severity,
            "summary": a.summary,
            "detected_at": a.detected_at.isoformat() if a.detected_at else None,
        }
        for a in anomalies
    ]


# =============================================================================
# EXPOSURE STATUS ROUTE
# =============================================================================

@router.get(
    "/exposure-status",
    summary="Retrieve continuous monitoring grid status",
    description="Returns high-level statistics of the continuous scheduler, active agents, and anomalies.",
)
async def get_exposure_status(
    organization_id: UUID = Query(..., description="Organization workspace ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """Get status."""
    await enforce_grid_access(current_user.id, organization_id, rbac)

    # 1. Total agents count
    agent_count_stmt = select(func.count(GridAgent.id)).where(
        and_(
            GridAgent.organization_id == organization_id,
            GridAgent.status == "active"
        )
    )
    agents_active = (await db.execute(agent_count_stmt)).scalar() or 0

    # 2. Total mutations count
    mutation_count_stmt = select(func.count(ExposureMutation.id)).where(
        ExposureMutation.organization_id == organization_id
    )
    total_mutations = (await db.execute(mutation_count_stmt)).scalar() or 0

    # 3. Total anomalies count (last 24 hours)
    yesterday = datetime.utcnow() - func.cast(func.concat("24", " hours"), func.interval)
    # Using python timezone-less calculation to work across both SQLite and Postgres
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    anomaly_count_stmt = select(func.count(AnomalyEvent.id)).where(
        and_(
            AnomalyEvent.organization_id == organization_id,
            AnomalyEvent.detected_at >= cutoff
        )
    )
    recent_anomalies = (await db.execute(anomaly_count_stmt)).scalar() or 0

    # Determine grid status indicator
    grid_status = "nominal"
    if recent_anomalies > 5:
        grid_status = "degraded"
    elif recent_anomalies > 2:
        grid_status = "warning"

    return {
        "organization_id": str(organization_id),
        "grid_health": "healthy",
        "grid_status": grid_status,
        "active_agents_count": agents_active,
        "total_mutations_count": total_mutations,
        "recent_anomalies_count": recent_anomalies,
        "last_scan_cycle": datetime.utcnow().isoformat(),
    }


# =============================================================================
# TRIGGER REVALIDATION ROUTE
# =============================================================================

@router.post(
    "/trigger-cycle",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger continuous monitoring scan cycle manually",
    description="Forces a scheduler cycle to scan assets for mutations. Requires RUN_SCANS permission.",
)
async def trigger_monitoring_cycle(
    organization_id: UUID = Query(..., description="Organization workspace ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """Trigger cycle."""
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.RUN_SCANS)

    grid_service = GridService(db)
    res = await grid_service.run_continuous_monitoring(organization_id)

    return {
        "status": "triggered",
        "details": res,
    }
