"""
Attack reasoning API routes.
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
from backend.services.attack_service import AttackService

router = APIRouter(prefix="/attack", tags=["attack"])


async def get_attack_service(db: AsyncSession = Depends(get_db)) -> AttackService:
    return AttackService(db)


async def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def _authorize(user: User, organization_id: UUID, rbac: RBACService, permission: Permission) -> None:
    await rbac.validate_workspace_access(user.id, organization_id)
    await rbac.check_permission(user.id, organization_id, permission)


@router.get("/paths", summary="Advanced attack paths")
async def get_attack_paths(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    asset_id: UUID | None = Query(None, description="Optional source asset ID"),
    current_user: User = Depends(get_current_user),
    attack_service: AttackService = Depends(get_attack_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _authorize(current_user, organization_id, rbac, Permission.VIEW_FINDINGS)
    return await attack_service.generate_attack_analysis(organization_id, source_asset_id=asset_id)


@router.get("/blast-radius", summary="Attack blast radius")
async def get_blast_radius(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    asset_id: UUID | None = Query(None, description="Optional focal asset ID"),
    current_user: User = Depends(get_current_user),
    attack_service: AttackService = Depends(get_attack_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _authorize(current_user, organization_id, rbac, Permission.VIEW_ASSETS)
    return await attack_service.calculate_exploitability(organization_id, asset_id=asset_id)


@router.get("/privilege-chains", summary="Privilege chain reasoning")
async def get_privilege_chains(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    attack_service: AttackService = Depends(get_attack_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _authorize(current_user, organization_id, rbac, Permission.VIEW_FINDINGS)
    analysis = await attack_service.generate_attack_analysis(organization_id)
    return {
        "organization_id": organization_id,
        "privilege_chain": analysis.get("privilege_chain"),
        "auth_inheritance": analysis.get("auth_inheritance"),
    }


@router.get("/lateral-movement", summary="Lateral movement simulation")
async def get_lateral_movement(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    attack_service: AttackService = Depends(get_attack_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _authorize(current_user, organization_id, rbac, Permission.VIEW_ASSETS)
    analysis = await attack_service.generate_attack_analysis(organization_id)
    return {
        "organization_id": organization_id,
        "lateral_movement": analysis.get("lateral_movement"),
        "trust_boundary": analysis.get("trust_boundary"),
        "summary": analysis.get("summary"),
    }