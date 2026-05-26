"""
Developer ecosystem management routes.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.core.permissions import Permission, RBACService
from backend.database.session import get_db
from backend.models.developer_application import DeveloperApplication
from backend.models.user import User
from backend.services.developer_service import DeveloperService
from backend.webhooks.webhook_manager import WebhookManager

router = APIRouter(prefix="/developer", tags=["developer"])


async def get_developer_service(db: AsyncSession = Depends(get_db)) -> DeveloperService:
    return DeveloperService(db)


async def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


class ApiKeyRequest(BaseModel):
    organization_id: UUID
    name: str
    application_name: str | None = None
    permissions: list[str] = Field(default_factory=list)
    rate_limit: dict | None = None


class WebhookRequest(BaseModel):
    organization_id: UUID
    endpoint: str
    subscribed_events: list[str] = Field(default_factory=list)


def _require_api_access(rbac: RBACService, user: User, organization_id: UUID):
    return rbac.validate_workspace_access(user.id, organization_id)


@router.post("/api-key", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: ApiKeyRequest,
    current_user: User = Depends(get_current_user),
    developer_service: DeveloperService = Depends(get_developer_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    await _require_api_access(rbac, current_user, request.organization_id)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.MANAGE_ORG)
    return await developer_service.generate_api_key(
        organization_id=request.organization_id,
        name=request.name,
        permissions=request.permissions or [Permission.VIEW_FINDINGS.value, Permission.VIEW_ASSETS.value],
        rate_limit=request.rate_limit,
        application_name=request.application_name,
    )


@router.get("/usage")
async def usage_summary(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    developer_service: DeveloperService = Depends(get_developer_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    await _require_api_access(rbac, current_user, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_ORG)
    return await developer_service.generate_usage_summary(organization_id)


@router.post("/webhook")
async def register_webhook(
    request: WebhookRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    await _require_api_access(rbac, current_user, request.organization_id)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.MANAGE_ORG)
    manager = WebhookManager(db)
    subscription = await manager.register_webhook(
        organization_id=request.organization_id,
        endpoint=request.endpoint,
        subscribed_events=request.subscribed_events,
    )
    return subscription


@router.get("/apps")
async def list_apps(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac_service),
) -> list[dict]:
    await _require_api_access(rbac, current_user, organization_id)
    result = await db.execute(
        select(DeveloperApplication).where(DeveloperApplication.organization_id == organization_id),
    )
    apps = result.scalars().all()
    return [
        {
            "id": app.id,
            "organization_id": app.organization_id,
            "name": app.name,
            "api_key_id": app.api_key_id,
            "usage_stats": app.usage_stats or {},
            "created_at": app.created_at,
        }
        for app in apps
    ]
