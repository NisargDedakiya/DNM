"""
Notification API routes.

Provides secured, organization-isolated access to notification history,
preferences, and test alert routing.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.core.permissions import Permission, RBACService
from backend.database.session import get_db
from backend.models.notification import NotificationType
from backend.models.user import User
from backend.services.alert_router_service import AlertRouterService
from backend.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationTestRequest(BaseModel):
    organization_id: UUID
    notification_type: str = Field(default=NotificationType.MONITORING_ALERT.value)
    severity: str = Field(default="medium")
    title: str = Field(default="Test security notification")
    message: str = Field(default="This is a test notification from NisargHunter AI")
    metadata: dict[str, Any] | None = None


class NotificationPreferencesRequest(BaseModel):
    organization_id: UUID
    severity_channels: dict[str, list[str]] = Field(default_factory=dict)
    slack_webhook_url: str = ""
    discord_webhook_url: str = ""
    emails: list[str] = Field(default_factory=list)
    rate_limit_per_minute: dict[str, int] = Field(default_factory=dict)


async def get_rbac(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(db)


async def get_alert_router(
    notification_service: NotificationService = Depends(get_notification_service),
) -> AlertRouterService:
    return AlertRouterService(notification_service)


def _serialize_notification(notification: Any) -> dict[str, Any]:
    return {
        "id": str(notification.id),
        "organization_id": str(notification.organization_id),
        "notification_type": str(notification.notification_type),
        "severity": str(notification.severity),
        "title": notification.title,
        "message": notification.message,
        "channel": str(notification.channel),
        "status": str(notification.status),
        "created_at": notification.created_at,
        "delivered_at": notification.delivered_at,
        "delivery_attempts": notification.delivery_attempts,
        "error_message": notification.error_message,
        "metadata": notification.notification_metadata,
    }


@router.get(
    "",
    summary="Get notifications",
    description="Return latest organization notifications with optional filtering.",
)
async def get_notifications(
    organization_id: UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    channel: str | None = Query(None),
    severity: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
    rbac: RBACService = Depends(get_rbac),
) -> list[dict[str, Any]]:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)

    notifications = await notification_service.get_notification_history(
        organization_id=organization_id,
        limit=limit,
        offset=0,
        channel=channel,
        severity=severity,
        status=status_filter,
    )
    return [_serialize_notification(item) for item in notifications]


@router.get(
    "/history",
    summary="Get notification history",
    description="Return paginated historical notification records for an organization.",
)
async def get_notification_history(
    organization_id: UUID = Query(...),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
    channel: str | None = Query(None),
    severity: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)

    items = await notification_service.get_notification_history(
        organization_id=organization_id,
        limit=limit,
        offset=offset,
        channel=channel,
        severity=severity,
        status=status_filter,
    )

    return {
        "total": len(items),
        "limit": limit,
        "offset": offset,
        "notifications": [_serialize_notification(item) for item in items],
    }


@router.post(
    "/test",
    summary="Send test notification",
    description="Trigger a routed test notification for policy and integration validation.",
)
async def send_test_notification(
    request: NotificationTestRequest,
    current_user: User = Depends(get_current_user),
    alert_router: AlertRouterService = Depends(get_alert_router),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, request.organization_id)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.MANAGE_FINDINGS)

    try:
        routed = await alert_router.route_alert(
            organization_id=request.organization_id,
            notification_type=request.notification_type,
            severity=request.severity,
            title=request.title,
            message=request.message,
            metadata={
                "source": "notifications_test_endpoint",
                "triggered_by": str(current_user.id),
                **(request.metadata or {}),
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "routed_count": len(routed),
        "notifications": [_serialize_notification(item) for item in routed],
    }


@router.put(
    "/preferences",
    summary="Update notification preferences",
    description="Update organization routing preferences and channel configuration.",
)
async def update_notification_preferences(
    request: NotificationPreferencesRequest,
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, request.organization_id)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.MANAGE_FINDINGS)

    safe_channels = {"websocket", "email", "slack", "discord"}
    for _, channel_list in request.severity_channels.items():
        for channel in channel_list:
            if channel not in safe_channels:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported channel '{channel}'",
                )

    preferences = await notification_service.update_preferences(
        organization_id=request.organization_id,
        preferences=request.model_dump(exclude={"organization_id"}),
    )

    return {
        "organization_id": str(request.organization_id),
        "preferences": preferences,
    }
