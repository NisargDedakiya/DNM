"""
Security hardening API routes.
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
from backend.services.security_service import SecurityService

router = APIRouter(prefix="/security", tags=["security"])


async def get_security_service(db: AsyncSession = Depends(get_db)) -> SecurityService:
    return SecurityService(db)


async def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def _authorize(user: User, organization_id: UUID, rbac: RBACService, permission: Permission) -> None:
    await rbac.validate_workspace_access(user.id, organization_id)
    await rbac.check_permission(user.id, organization_id, permission)


@router.get("/audit", summary="Security audit trail")
async def get_security_audit(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    security_service: SecurityService = Depends(get_security_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _authorize(current_user, organization_id, rbac, Permission.VIEW_FINDINGS)
    return await security_service.get_audit_timeline(organization_id, limit=limit)


@router.get("/events", summary="Security events")
async def get_security_events(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    security_service: SecurityService = Depends(get_security_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _authorize(current_user, organization_id, rbac, Permission.VIEW_FINDINGS)
    return await security_service.get_security_events(organization_id)


@router.get("/rate-limits", summary="Rate limit status")
async def get_rate_limits(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    security_service: SecurityService = Depends(get_security_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _authorize(current_user, organization_id, rbac, Permission.VIEW_FINDINGS)
    return await security_service.get_rate_limit_status(organization_id)


@router.get("/recovery-status", summary="Recovery state")
async def get_recovery_status(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    security_service: SecurityService = Depends(get_security_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _authorize(current_user, organization_id, rbac, Permission.MANAGE_ORG)
    return await security_service.get_recovery_status(organization_id)