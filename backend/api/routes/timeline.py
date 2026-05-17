"""
Timeline API routes: historical attack surface intelligence endpoints.

All routes:
- Require JWT authentication via get_current_user dependency.
- Enforce workspace isolation via RBAC validate_workspace_access.
- Use async FastAPI patterns consistent with the rest of the codebase.
- Are read-only (GET) – timeline data is never mutated through the API.

Route map
---------
GET /timeline/assets/{asset_id}          → per-asset historical timeline
GET /timeline/exposures                  → org exposure evolution timeline
GET /timeline/changes                    → paginated change history feed
GET /timeline/snapshots                  → paginated snapshot history list
GET /timeline/snapshots/{snapshot_id}    → full snapshot payload
GET /timeline/analytics                  → attack surface analytics dashboard
POST /timeline/snapshots/capture         → manually trigger a snapshot
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.core.permissions import Permission, RBACService
from backend.services.snapshot_service import SnapshotService
from backend.services.change_detection_service import ChangeDetectionService
from backend.services.timeline_service import TimelineService

router = APIRouter(prefix="/timeline", tags=["timeline"])


# ── Dependency helpers ────────────────────────────────────────────────────────

async def get_rbac(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def get_snapshot_service(db: AsyncSession = Depends(get_db)) -> SnapshotService:
    return SnapshotService(db)


async def get_change_detection_service(db: AsyncSession = Depends(get_db)) -> ChangeDetectionService:
    return ChangeDetectionService(db)


async def get_timeline_service(db: AsyncSession = Depends(get_db)) -> TimelineService:
    return TimelineService(db)


# ── Workspace isolation helper ─────────────────────────────────────────────────

async def _enforce_workspace(
    user_id: UUID,
    organization_id: UUID,
    rbac: RBACService,
) -> None:
    """Raise 403 if the user is not a member of the target organisation."""
    await rbac.validate_workspace_access(user_id, organization_id)


# =============================================================================
# ASSET TIMELINE
# =============================================================================

@router.get(
    "/assets/{asset_id}",
    summary="Asset historical timeline",
    description=(
        "Returns the complete historical timeline for a single asset, "
        "including all detected change events, risk trend data, and summary statistics. "
        "Workspace isolation is enforced via organization_id."
    ),
)
async def get_asset_timeline(
    asset_id: UUID,
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    limit: int = Query(100, ge=1, le=500, description="Max change events to return"),
    current_user: User = Depends(get_current_user),
    timeline_svc: TimelineService = Depends(get_timeline_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Get a per-asset timeline combining metadata, change events, and risk trend.

    **Requires**: VIEW_ASSETS permission.

    Returns
    -------
    JSON with fields:
    - ``asset`` – asset metadata snapshot
    - ``timeline`` – list of change events (newest first)
    - ``summary`` – change type counts
    - ``risk_trend`` – chronological (timestamp, score) pairs for charts
    """
    await _enforce_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    return await timeline_svc.generate_asset_timeline(
        organization_id=organization_id,
        asset_id=asset_id,
        limit=limit,
    )


# =============================================================================
# EXPOSURE TIMELINE
# =============================================================================

@router.get(
    "/exposures",
    summary="Exposure evolution timeline",
    description=(
        "Returns a day-by-day breakdown of exposure changes (new, resolved, updated) "
        "over a configurable lookback window. Useful for tracking risk posture evolution."
    ),
)
async def get_exposure_timeline(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    days: int = Query(30, ge=1, le=365, description="Lookback window in days"),
    asset_id: UUID | None = Query(None, description="Optional: limit to a single asset"),
    current_user: User = Depends(get_current_user),
    timeline_svc: TimelineService = Depends(get_timeline_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Get organisation-level exposure evolution timeline.

    **Requires**: VIEW_FINDINGS permission.

    Returns
    -------
    JSON with:
    - ``daily_breakdown`` – per-day new/resolved/changed counts
    - ``totals`` – aggregate for the period
    - ``current_active`` – live count of active exposures
    - ``severity_trend`` – daily breakdown by severity level
    """
    await _enforce_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)

    return await timeline_svc.generate_exposure_timeline(
        organization_id=organization_id,
        days=days,
        asset_id=asset_id,
    )


# =============================================================================
# CHANGE HISTORY FEED
# =============================================================================

@router.get(
    "/changes",
    summary="Paginated change history",
    description=(
        "Returns a paginated feed of all detected infrastructure changes. "
        "Supports filtering by change type, severity, asset, program, and time window."
    ),
)
async def list_changes(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    change_type: str | None = Query(
        None,
        description=(
            "Filter by change type: new_asset, removed_asset, new_endpoint, "
            "removed_endpoint, technology_change, exposure_change, new_exposure, "
            "resolved_exposure, risk_change"
        ),
    ),
    severity: str | None = Query(
        None,
        description="Filter by severity: critical, high, medium, low, info",
    ),
    asset_id: UUID | None = Query(None, description="Filter to a specific asset"),
    program_id: UUID | None = Query(None, description="Filter to a specific program"),
    since: datetime | None = Query(None, description="ISO-8601 start datetime"),
    until: datetime | None = Query(None, description="ISO-8601 end datetime"),
    current_user: User = Depends(get_current_user),
    timeline_svc: TimelineService = Depends(get_timeline_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Paginated, filterable change history feed.

    **Requires**: VIEW_ASSETS permission.

    Returns
    -------
    JSON with:
    - ``events`` – list of change event dicts
    - ``total``  – total matching count (for pagination UI)
    - ``filters`` – echo of active filters
    """
    await _enforce_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    return await timeline_svc.build_change_history(
        organization_id=organization_id,
        limit=limit,
        offset=offset,
        change_type=change_type,
        severity=severity,
        asset_id=asset_id,
        program_id=program_id,
        since=since,
        until=until,
    )


# =============================================================================
# SNAPSHOT HISTORY LIST
# =============================================================================

@router.get(
    "/snapshots",
    summary="Snapshot history listing",
    description=(
        "Returns a paginated list of historical recon snapshots (metadata only, "
        "no payload). Use GET /timeline/snapshots/{id} to fetch the full payload."
    ),
)
async def list_snapshots(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    snapshot_type: str | None = Query(
        None,
        description="Filter by type: assets, endpoints, technologies, exposures, findings",
    ),
    program_id: UUID | None = Query(None, description="Filter to a specific program"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    timeline_svc: TimelineService = Depends(get_timeline_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    List historical snapshots with lightweight metadata.

    **Requires**: VIEW_ASSETS permission.
    """
    await _enforce_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    return await timeline_svc.get_snapshot_history(
        organization_id=organization_id,
        snapshot_type=snapshot_type,
        program_id=program_id,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# SINGLE SNAPSHOT PAYLOAD
# =============================================================================

@router.get(
    "/snapshots/{snapshot_id}",
    summary="Fetch snapshot payload",
    description="Returns the full immutable snapshot payload for a given snapshot ID.",
)
async def get_snapshot(
    snapshot_id: UUID,
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    snapshot_svc: SnapshotService = Depends(get_snapshot_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Retrieve a specific snapshot with full payload.

    **Requires**: VIEW_ASSETS permission.
    Workspace isolation is enforced – the snapshot must belong to ``organization_id``.
    """
    await _enforce_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    snap = await snapshot_svc.get_snapshot_by_id(snapshot_id, organization_id)
    if snap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not found or access denied",
        )

    return {
        "id": str(snap.id),
        "snapshot_type": snap.snapshot_type,
        "organization_id": str(snap.organization_id),
        "program_id": str(snap.program_id) if snap.program_id else None,
        "trigger_source": snap.trigger_source,
        "triggered_by_scan_id": str(snap.triggered_by_scan_id) if snap.triggered_by_scan_id else None,
        "notes": snap.notes,
        "created_at": snap.created_at.isoformat() if snap.created_at else None,
        "snapshot_data": snap.snapshot_data,
    }


# =============================================================================
# ATTACK SURFACE ANALYTICS
# =============================================================================

@router.get(
    "/analytics",
    summary="Attack surface analytics",
    description=(
        "Returns high-level analytics: asset growth over time, technology churn, "
        "risk drift, top changed assets, and current exposure distribution. "
        "Configurable lookback window up to 365 days."
    ),
)
async def get_analytics(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    days: int = Query(90, ge=7, le=365, description="Analytics lookback window in days"),
    current_user: User = Depends(get_current_user),
    timeline_svc: TimelineService = Depends(get_timeline_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Attack surface analytics for the configured time window.

    **Requires**: VIEW_ASSETS permission.

    Returns
    -------
    JSON with:
    - ``asset_growth`` – weekly new vs removed asset counts
    - ``technology_churn`` – weekly tech change counts
    - ``risk_drift`` – weekly net risk score delta
    - ``top_changed_assets`` – top 10 most-changed assets
    - ``exposure_distribution`` – current exposure counts by risk level
    """
    await _enforce_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    return await timeline_svc.get_attack_surface_analytics(
        organization_id=organization_id,
        days=days,
    )


# =============================================================================
# MANUAL SNAPSHOT CAPTURE
# =============================================================================

@router.post(
    "/snapshots/capture",
    status_code=status.HTTP_201_CREATED,
    summary="Manually capture attack surface snapshot",
    description=(
        "Triggers an immediate full-surface snapshot capture for the given organisation. "
        "Captures all five domains: assets, endpoints, technologies, exposures. "
        "Requires RUN_SCANS permission."
    ),
)
async def capture_snapshot(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    program_id: UUID | None = Query(None, description="Optional program scope"),
    notes: str | None = Query(None, description="Optional notes for this snapshot"),
    current_user: User = Depends(get_current_user),
    snapshot_svc: SnapshotService = Depends(get_snapshot_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Manually trigger a full attack surface snapshot.

    **Requires**: RUN_SCANS permission (analyst+).

    Returns
    -------
    JSON with one entry per captured domain and its snapshot ID / record count.
    """
    await _enforce_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.RUN_SCANS)

    try:
        snapshots = await snapshot_svc.create_full_surface_snapshot(
            organization_id=organization_id,
            program_id=program_id,
            trigger_source="manual",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Snapshot capture failed: {exc}",
        ) from exc

    # Attach notes to each snapshot if provided
    # (notes are informational; no mutation of already-committed rows)
    return {
        "status": "captured",
        "snapshots": {
            domain: {
                "id": str(snap.id),
                "snapshot_type": snap.snapshot_type,
                "record_count": (
                    snap.snapshot_data.get("record_count", 0)
                    if isinstance(snap.snapshot_data, dict)
                    else 0
                ),
                "created_at": snap.created_at.isoformat() if snap.created_at else None,
            }
            for domain, snap in snapshots.items()
        },
        "notes": notes,
    }


# =============================================================================
# DIFF TWO SNAPSHOTS
# =============================================================================

@router.post(
    "/snapshots/diff",
    summary="Diff two snapshots",
    description=(
        "Compare a before/after pair of snapshots and persist the detected "
        "change events. Both snapshots must belong to the same organisation. "
        "Requires RUN_SCANS permission."
    ),
)
async def diff_snapshots(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    before_snapshot_id: UUID = Query(..., description="Source (before) snapshot ID"),
    after_snapshot_id: UUID = Query(..., description="Target (after) snapshot ID"),
    snapshot_type: str = Query(
        ...,
        description="Domain to diff: assets, endpoints, technologies, exposures",
    ),
    program_id: UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    detection_svc: ChangeDetectionService = Depends(get_change_detection_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Diff two snapshots and persist the resulting change events.

    **Requires**: RUN_SCANS permission.
    """
    await _enforce_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.RUN_SCANS)

    DIFF_MAP = {
        "assets": detection_svc.detect_asset_changes,
        "endpoints": detection_svc.detect_endpoint_changes,
        "technologies": detection_svc.detect_technology_changes,
        "exposures": detection_svc.detect_exposure_changes,
    }

    diff_fn = DIFF_MAP.get(snapshot_type)
    if diff_fn is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown snapshot_type '{snapshot_type}'. Must be one of: {list(DIFF_MAP.keys())}",
        )

    try:
        events = await diff_fn(
            organization_id=organization_id,
            source_snapshot_id=before_snapshot_id,
            target_snapshot_id=after_snapshot_id,
            program_id=program_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Diff failed: {exc}",
        ) from exc

    return {
        "status": "diff_complete",
        "snapshot_type": snapshot_type,
        "before_snapshot_id": str(before_snapshot_id),
        "after_snapshot_id": str(after_snapshot_id),
        "change_events_detected": len(events),
        "severity_breakdown": {
            sev: sum(1 for e in events if e.severity == sev)
            for sev in ["critical", "high", "medium", "low", "info"]
        },
    }
