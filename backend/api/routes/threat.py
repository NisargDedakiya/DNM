"""
Threat intelligence API routes.
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
from backend.services.threat_service import ThreatService

router = APIRouter(prefix="/threat", tags=["threat"])


async def get_threat_service(db: AsyncSession = Depends(get_db)) -> ThreatService:
    return ThreatService(db)


async def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def _authorize(user: User, organization_id: UUID, rbac: RBACService, permission: Permission) -> None:
    await rbac.validate_workspace_access(user.id, organization_id)
    await rbac.check_permission(user.id, organization_id, permission)


@router.get("/cves", summary="CVE intelligence for an organization")
async def get_cve_intelligence(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    asset_id: UUID | None = Query(None, description="Optional asset ID"),
    current_user: User = Depends(get_current_user),
    threat_service: ThreatService = Depends(get_threat_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _authorize(current_user, organization_id, rbac, Permission.VIEW_FINDINGS)
    if asset_id:
        return await threat_service.correlate_external_threats(organization_id, asset_id)
    return await threat_service.generate_threat_summary(organization_id)


@router.get("/external-exposure", summary="External exposure intelligence")
async def get_external_exposure(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    asset_id: UUID | None = Query(None, description="Optional asset ID"),
    current_user: User = Depends(get_current_user),
    threat_service: ThreatService = Depends(get_threat_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _authorize(current_user, organization_id, rbac, Permission.VIEW_FINDINGS)
    if asset_id:
        return await threat_service.enrich_exposure(organization_id, asset_id)
    return await threat_service.generate_threat_summary(organization_id)


@router.get("/ip-reputation", summary="IP reputation intelligence")
async def get_ip_reputation(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    ip_address: str | None = Query(None, description="Optional IP address"),
    current_user: User = Depends(get_current_user),
    threat_service: ThreatService = Depends(get_threat_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _authorize(current_user, organization_id, rbac, Permission.VIEW_ASSETS)
    summary = await threat_service.generate_threat_summary(organization_id)
    if ip_address:
        from backend.threat.ip_reputation import analyze_ip_reputation

        summary["ip_reputation"] = analyze_ip_reputation(ip_address)
    return summary


@router.get("/intelligence", summary="Unified threat intelligence summary")
async def get_threat_intelligence(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    threat_service: ThreatService = Depends(get_threat_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _authorize(current_user, organization_id, rbac, Permission.VIEW_FINDINGS)
    return await threat_service.generate_threat_summary(organization_id)