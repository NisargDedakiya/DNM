"""
Enterprise SSO routes for SAML, OAuth, and private workspace sessions.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.core.permissions import Permission, RBACService
from backend.database.session import get_db
from backend.models.user import User
from backend.services.sso_service import SSOService

router = APIRouter(prefix="/sso", tags=["sso"])


async def get_sso_service(db: AsyncSession = Depends(get_db)) -> SSOService:
    return SSOService(db)


async def get_rbac(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def _require_workspace(user_id: UUID, organization_id: UUID, rbac: RBACService) -> None:
    await rbac.validate_workspace_access(user_id, organization_id)


@router.post("/login", summary="Enterprise SSO login")
async def enterprise_login(
    organization_id: UUID,
    provider: str,
    payload: dict[str, Any],
    sso_service: SSOService = Depends(get_sso_service),
) -> dict[str, Any]:
    result = await sso_service.authenticate_enterprise_request(organization_id, provider, payload)
    if not result.get("authenticated"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result.get("reason", "SSO authentication failed"))
    return result


@router.post("/saml", summary="SAML authentication")
async def saml_login(
    organization_id: UUID,
    saml_response: str,
    audience: str | None = None,
    sso_service: SSOService = Depends(get_sso_service),
) -> dict[str, Any]:
    result = await sso_service.authenticate_enterprise_request(
        organization_id,
        "saml",
        {"saml_response": saml_response, "audience": audience},
    )
    if not result.get("authenticated"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result.get("reason", "Invalid SAML response"))
    return result


@router.post("/oauth", summary="OAuth federation login")
async def oauth_login(
    organization_id: UUID,
    provider: str,
    access_token: str,
    workspace_id: str | None = None,
    sso_service: SSOService = Depends(get_sso_service),
) -> dict[str, Any]:
    result = await sso_service.authenticate_enterprise_request(
        organization_id,
        provider,
        {"access_token": access_token, "workspace_id": workspace_id},
    )
    if not result.get("authenticated"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result.get("reason", "Invalid OAuth token"))
    return result


@router.get("/session", summary="Enterprise session state")
async def get_session_state(
    session_id: str,
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_ORGANIZATION)
    from backend.sso.session_manager import validate_session

    return validate_session(session_id, str(organization_id))


@router.post("/logout", summary="Enterprise logout")
async def enterprise_logout(
    session_id: str,
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_ORGANIZATION)
    from backend.sso.session_manager import terminate_session

    return terminate_session(session_id)
