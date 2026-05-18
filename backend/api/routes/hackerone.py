"""
HackerOne integration API routes.

Endpoints:
- POST /hackerone/connect
- GET  /hackerone/programs
- POST /hackerone/sync
- GET  /hackerone/reports
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.hackerone import HackerOneClient, HackerOneAPIError, HackerOneAuthError
from backend.core.permissions import Permission, RBACService
from backend.database.session import get_db
from backend.models.hackerone_program import HackerOneProgram
from backend.models.hackerone_report import HackerOneReport
from backend.models.user import User
from backend.services.hackerone_sync_service import HackerOneSyncService

router = APIRouter(prefix="/hackerone", tags=["hackerone"])


class HackerOneConnectRequest(BaseModel):
    organization_id: UUID
    username: str = Field(min_length=1, max_length=255)
    api_token: str = Field(min_length=1, max_length=512)


class HackerOneSyncRequest(BaseModel):
    organization_id: UUID
    username: str = Field(min_length=1, max_length=255)
    api_token: str = Field(min_length=1, max_length=512)


async def get_rbac(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def get_sync_svc(db: AsyncSession = Depends(get_db)) -> HackerOneSyncService:
    return HackerOneSyncService(db)


@router.post("/connect", summary="Validate HackerOne credentials")
async def connect_hackerone(
    request: HackerOneConnectRequest,
    current_user: User = Depends(get_current_user),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, request.organization_id)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.MANAGE_ASSETS)

    try:
        client = HackerOneClient(username=request.username, api_token=request.api_token)
        auth = await client.authenticate()
    except (HackerOneAuthError, HackerOneAPIError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return {
        "connected": True,
        "organization_id": str(request.organization_id),
        "program_count_hint": auth.get("program_count_hint", 0),
    }


@router.get("/programs", summary="List synced HackerOne programs")
async def list_hackerone_programs(
    organization_id: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    result = await db.execute(
        select(HackerOneProgram).where(HackerOneProgram.organization_id == organization_id)
    )
    programs = result.scalars().all()

    return {
        "total": len(programs),
        "programs": [
            {
                "id": str(p.id),
                "organization_id": str(p.organization_id),
                "hackerone_program_id": p.hackerone_program_id,
                "handle": p.handle,
                "name": p.name,
                "bounty_enabled": p.bounty_enabled,
                "offers_bounties": p.offers_bounties,
                "synced_at": p.synced_at,
                "created_at": p.created_at,
            }
            for p in programs
        ],
    }


@router.post("/sync", summary="Sync HackerOne programs and scopes")
async def sync_hackerone(
    request: HackerOneSyncRequest,
    current_user: User = Depends(get_current_user),
    sync_svc: HackerOneSyncService = Depends(get_sync_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, request.organization_id)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.MANAGE_ASSETS)

    try:
        result = await sync_svc.sync_programs(
            organization_id=request.organization_id,
            username=request.username,
            api_token=request.api_token,
        )
    except (HackerOneAuthError, HackerOneAPIError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return result


@router.get("/reports", summary="Sync and list my HackerOne reports")
async def get_hackerone_reports(
    organization_id: UUID = Query(...),
    h1_username: str = Header(..., alias="X-HackerOne-Username"),
    h1_token: str = Header(..., alias="X-HackerOne-Token"),
    current_user: User = Depends(get_current_user),
    sync_svc: HackerOneSyncService = Depends(get_sync_svc),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)

    try:
        await sync_svc.sync_reports(
            organization_id=organization_id,
            username=h1_username,
            api_token=h1_token,
        )
    except (HackerOneAuthError, HackerOneAPIError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    result = await db.execute(
        select(HackerOneReport).where(HackerOneReport.organization_id == organization_id)
    )
    reports = result.scalars().all()

    return {
        "total": len(reports),
        "reports": [
            {
                "id": str(r.id),
                "organization_id": str(r.organization_id),
                "hackerone_report_id": r.hackerone_report_id,
                "title": r.title,
                "severity": r.severity,
                "state": r.state,
                "submitted_at": r.submitted_at,
            }
            for r in reports
        ],
    }
