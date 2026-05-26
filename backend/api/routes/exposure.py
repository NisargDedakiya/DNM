"""
Exposure intelligence API routes.
Endpoints for exposure analysis, scoring, and prioritization.
"""
from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.core.permissions import Permission, RBACService
from backend.services.exposure_service import ExposureService
from backend.services.risk_service import RiskService
from backend.services.fingerprinting_service import FingerprintingService

router = APIRouter(prefix="/exposures", tags=["exposures"])
timeline_router = APIRouter(prefix="/exposure", tags=["exposure-timeline"])


async def get_exposure_service(db: AsyncSession = Depends(get_db)) -> ExposureService:
    """Dependency for exposure service."""
    return ExposureService(db)


async def get_risk_service(db: AsyncSession = Depends(get_db)) -> RiskService:
    """Dependency for risk service."""
    return RiskService(db)


async def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RBACService:
    """Dependency for RBAC service."""
    return RBACService(db)


async def get_timeline_exposure_service(db: AsyncSession = Depends(get_db)) -> ExposureService:
    return ExposureService(db)


# ============================================================================
# EXPOSURE ENDPOINTS
# ============================================================================


@router.get(
    "",
    summary="List organization exposures",
    description="Get all exposures for an organization",
)
async def list_exposures(
    organization_id: UUID,
    active_only: bool = Query(True),
    risk_level: str | None = Query(None),
    exposure_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    exposure_service: ExposureService = Depends(get_exposure_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> list[dict]:
    """
    List exposures for an organization.

    Args:
        organization_id: Organization ID
        active_only: Only active exposures
        risk_level: Filter by risk level
        exposure_type: Filter by exposure type
        limit: Result limit
        current_user: Current authenticated user
        exposure_service: Exposure service
        rbac: RBAC service

    Returns:
        list[dict]: Exposures with details

    Raises:
        HTTPException: 403 if not authorized
    """
    await rbac.validate_workspace_access(current_user.id, organization_id)

    exposures = await exposure_service.get_organization_exposures(
        organization_id=organization_id,
        active_only=active_only,
        risk_level=risk_level,
        exposure_type=exposure_type,
        limit=limit,
    )

    return [
        {
            "id": str(exposure.id),
            "asset_id": str(exposure.asset_id),
            "exposure_type": exposure.exposure_type,
            "risk_level": exposure.risk_level,
            "title": exposure.title,
            "description": exposure.description,
            "risk_score": round(exposure.risk_score, 2),
            "confidence_score": round(exposure.confidence_score, 2),
            "first_detected": exposure.first_detected.isoformat(),
            "last_detected": exposure.last_detected.isoformat(),
            "detection_count": exposure.detection_count,
            "is_active": exposure.is_active,
            "remediation_status": exposure.remediation_status,
        }
        for exposure in exposures
    ]


@router.get(
    "/{exposure_id}",
    summary="Get exposure details",
    description="Get detailed information about an exposure",
)
async def get_exposure(
    exposure_id: UUID,
    current_user: User = Depends(get_current_user),
    exposure_service: ExposureService = Depends(get_exposure_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    """Get exposure details."""
    exposure = await exposure_service.get_exposure(exposure_id)
    if not exposure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exposure not found",
        )

    await rbac.validate_workspace_access(current_user.id, exposure.organization_id)

    # Get categorization
    categorization = await exposure_service.categorize_exposure(
        exposure_type=exposure.exposure_type,
        fingerprint_data=exposure.fingerprint_data,
    )

    # Get history
    history = await exposure_service.get_exposure_history(exposure_id, limit=5)

    return {
        "id": str(exposure.id),
        "asset_id": str(exposure.asset_id),
        "exposure_type": exposure.exposure_type,
        "risk_level": exposure.risk_level,
        "title": exposure.title,
        "description": exposure.description,
        "risk_score": round(exposure.risk_score, 2),
        "confidence_score": round(exposure.confidence_score, 2),
        "first_detected": exposure.first_detected.isoformat(),
        "last_detected": exposure.last_detected.isoformat(),
        "detection_count": exposure.detection_count,
        "is_active": exposure.is_active,
        "remediation_status": exposure.remediation_status,
        "remediation_notes": exposure.remediation_notes,
        "evidence": exposure.evidence,
        "fingerprint_data": exposure.fingerprint_data,
        "categorization": categorization,
        "recent_changes": [
            {
                "change_type": h.change_type,
                "created_at": h.created_at.isoformat(),
                "change_reason": h.change_reason,
            }
            for h in history
        ],
    }


@router.get(
    "/assets/{asset_id}/exposures",
    summary="Get asset exposures",
    description="Get all exposures for an asset",
)
async def get_asset_exposures(
    asset_id: UUID,
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    exposure_service: ExposureService = Depends(get_exposure_service),
    rbac: RBACService = Depends(get_rbac_service),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get exposures for an asset."""
    # Verify user access (would need to check asset's org)
    exposures = await exposure_service.get_asset_exposures(
        asset_id=asset_id,
        active_only=active_only,
    )

    return [
        {
            "id": str(exposure.id),
            "asset_id": str(exposure.asset_id),
            "exposure_type": exposure.exposure_type,
            "risk_level": exposure.risk_level,
            "title": exposure.title,
            "description": exposure.description,
            "risk_score": round(exposure.risk_score, 2),
            "confidence_score": round(exposure.confidence_score, 2),
            "first_detected": exposure.first_detected.isoformat(),
            "last_detected": exposure.last_detected.isoformat(),
            "detection_count": exposure.detection_count,
            "is_active": exposure.is_active,
        }
        for exposure in exposures
    ]


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================


@router.get(
    "/analytics/summary",
    summary="Get exposure analytics summary",
    description="Get overview of exposures and risk scoring",
)
async def get_exposure_summary(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    """
    Get exposure analytics summary for organization.

    Args:
        organization_id: Organization ID
        current_user: Current authenticated user
        risk_service: Risk service
        rbac: RBAC service

    Returns:
        dict: Exposure summary and statistics

    Raises:
        HTTPException: 403 if not authorized
    """
    await rbac.validate_workspace_access(current_user.id, organization_id)

    # Get attack surface score
    surface_score = await risk_service.calculate_attack_surface_score(
        organization_id
    )

    # Get risk heatmap
    heatmap = await risk_service.get_risk_heatmap(organization_id)

    # Get remediation priorities
    priorities = await risk_service.get_remediation_priorities(
        organization_id, limit=10
    )

    return {
        "attack_surface": surface_score,
        "risk_distribution": heatmap["by_risk_level"],
        "exposure_types": heatmap["by_exposure_type"],
        "critical_assets": heatmap["critical_assets"],
        "top_priorities": priorities,
        "summary": {
            "total_exposures": surface_score["total_exposures"],
            "exposed_assets": surface_score["exposed_assets"],
            "overall_risk_level": surface_score["risk_level"],
            "overall_risk_score": surface_score["overall_score"],
        },
    }


@router.get(
    "/analytics/risk-heatmap",
    summary="Get risk heatmap",
    description="Get risk visualization data",
)
async def get_risk_heatmap(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    """Get risk heatmap data for visualization."""
    await rbac.validate_workspace_access(current_user.id, organization_id)

    heatmap = await risk_service.get_risk_heatmap(organization_id)
    return heatmap


@router.get(
    "/analytics/ranked",
    summary="Get ranked exposures",
    description="Get exposures ranked by risk priority",
)
async def get_ranked_exposures(
    organization_id: UUID,
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> list[dict]:
    """Get exposures ranked by risk priority."""
    await rbac.validate_workspace_access(current_user.id, organization_id)

    ranked = await risk_service.rank_exposures(
        organization_id,
        active_only=True,
        limit=limit,
    )

    return ranked


@router.get(
    "/analytics/remediation-priorities",
    summary="Get remediation priorities",
    description="Get prioritized list of remediation tasks",
)
async def get_remediation_priorities(
    organization_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> list[dict]:
    """Get prioritized remediation tasks."""
    await rbac.validate_workspace_access(current_user.id, organization_id)

    priorities = await risk_service.get_remediation_priorities(
        organization_id, limit=limit
    )

    return priorities


@router.get(
    "/analytics/asset-risk",
    summary="Get asset risk scores",
    description="Get risk scoring for all assets",
)
async def get_asset_risk_scores(
    organization_id: UUID,
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    rbac: RBACService = Depends(get_rbac_service),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    Get risk scores for all assets in organization.

    Args:
        organization_id: Organization ID
        limit: Result limit
        current_user: Current authenticated user
        risk_service: Risk service
        rbac: RBAC service
        db: Database session

    Returns:
        list[dict]: Asset risk scores
    """
    await rbac.validate_workspace_access(current_user.id, organization_id)

    # Would query assets and calculate risk for each
    # For now, returning empty (requires Asset query integration)
    return []


# ============================================================================
# CONTINUOUS TIMELINE ENDPOINTS
# ============================================================================


@timeline_router.get(
    "/timeline",
    summary="Continuous exposure timeline",
    description="Returns the latest exposure snapshot, drift analysis, risk evolution, and regression intelligence.",
)
async def get_exposure_timeline(
    organization_id: UUID = Query(...),
    asset: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    exposure_service: ExposureService = Depends(get_timeline_exposure_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)
    return await exposure_service.analyze_exposure_evolution(organization_id, asset=asset, limit=limit)


@timeline_router.get(
    "/drift",
    summary="Exposure drift analysis",
    description="Returns drift detection results for the most recent exposure snapshots.",
)
async def get_exposure_drift(
    organization_id: UUID = Query(...),
    asset: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    exposure_service: ExposureService = Depends(get_timeline_exposure_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)
    return await exposure_service.detect_high_risk_exposure_changes(organization_id, asset=asset, limit=limit)


@timeline_router.get(
    "/risk-evolution",
    summary="Risk evolution history",
    description="Returns historical risk deltas and escalation analysis for exposure tracking.",
)
async def get_risk_evolution(
    organization_id: UUID = Query(...),
    asset: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    exposure_service: ExposureService = Depends(get_timeline_exposure_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)
    return await exposure_service.risk_evolution.summarize_history(organization_id, asset=asset, limit=limit)


@timeline_router.get(
    "/regressions",
    summary="Exposure regression analysis",
    description="Returns repeated exposure patterns and reintroduced vulnerabilities.",
)
async def get_exposure_regressions(
    organization_id: UUID = Query(...),
    asset: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    exposure_service: ExposureService = Depends(get_timeline_exposure_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)
    return await exposure_service.regression_detector.detect_regressions(organization_id, asset=asset, limit=limit)


# ============================================================================
# ACKNOWLEDGEMENT ENDPOINTS
# ============================================================================


@router.post(
    "/{exposure_id}/acknowledge",
    summary="Acknowledge exposure",
    description="Mark exposure as acknowledged",
)
async def acknowledge_exposure(
    exposure_id: UUID,
    remediation_status: str,
    notes: str = "",
    current_user: User = Depends(get_current_user),
    exposure_service: ExposureService = Depends(get_exposure_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    """Acknowledge and mark exposure resolution."""
    exposure = await exposure_service.get_exposure(exposure_id)
    if not exposure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exposure not found",
        )

    await rbac.validate_workspace_access(current_user.id, exposure.organization_id)

    resolved = await exposure_service.resolve_exposure(
        exposure_id=exposure_id,
        remediation_status=remediation_status,
        notes=notes,
    )

    return {
        "id": str(resolved.id),
        "remediation_status": resolved.remediation_status,
        "is_active": resolved.is_active,
        "updated_at": resolved.updated_at.isoformat(),
    }
