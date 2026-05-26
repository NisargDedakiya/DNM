"""
Monitoring API routes for continuous recon management.
Handles monitoring rules, alerts, and real-time notifications.
"""
from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.core.permissions import Permission, RBACService
from backend.services.monitoring_service import MonitoringService
from backend.services.alert_service import AlertService
from backend.services.recon_pipeline_service import ReconPipelineService

from backend.schemas.organization import OrganizationResponse

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


async def get_monitoring_service(db: AsyncSession = Depends(get_db)) -> MonitoringService:
    """Dependency for monitoring service."""
    return MonitoringService(db)


async def get_alert_service(db: AsyncSession = Depends(get_db)) -> AlertService:
    """Dependency for alert service."""
    return AlertService(db)


async def get_recon_service(db: AsyncSession = Depends(get_db)) -> ReconPipelineService:
    """Dependency for recon pipeline service."""
    return ReconPipelineService(db)


async def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RBACService:
    """Dependency for RBAC service."""
    return RBACService(db)


# ============================================================================
# MONITORING RULES ENDPOINTS
# ============================================================================


@router.post(
    "/rules",
    status_code=status.HTTP_201_CREATED,
    summary="Create monitoring rule",
    description="Create a new recurring monitoring rule for automated reconnaissance",
)
async def create_monitoring_rule(
    organization_id: UUID,
    program_id: UUID,
    name: str,
    frequency: str = "daily",
    description: str | None = None,
    current_user: User = Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    """
    Create a new monitoring rule for automated reconnaissance.

    Allows analysts and above to create recurring scan rules on programs.
    Frequency options: hourly, daily, weekly.

    Args:
        organization_id: Organization ID
        program_id: Program to monitor
        name: Rule name
        frequency: Scan frequency (hourly, daily, weekly)
        description: Optional description
        current_user: Current authenticated user
        monitoring_service: Monitoring service
        rbac: RBAC service

    Returns:
        dict: Created monitoring rule

    Raises:
        HTTPException: 403 if no permission, 404 if program not found
    """
    # Validate workspace access
    await rbac.validate_workspace_access(current_user.id, organization_id)

    # Check permission
    await rbac.check_permission(
        current_user.id,
        organization_id,
        Permission.RUN_SCANS,
    )

    try:
        rule = await monitoring_service.create_monitoring_rule(
            organization_id=organization_id,
            program_id=program_id,
            name=name,
            frequency=frequency,
            description=description,
            created_by_id=current_user.id,
        )

        return {
            "id": rule.id,
            "name": rule.name,
            "program_id": rule.program_id,
            "frequency": rule.frequency,
            "description": rule.description,
            "enabled": rule.enabled,
            "created_at": rule.created_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/rules",
    summary="List monitoring rules",
    description="Get all monitoring rules for an organization",
)
async def list_monitoring_rules(
    organization_id: UUID,
    enabled_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> list[dict]:
    """
    List monitoring rules for an organization.

    Returns all monitoring rules user has access to.

    Args:
        organization_id: Organization ID
        enabled_only: Only return enabled rules
        current_user: Current authenticated user
        monitoring_service: Monitoring service
        rbac: RBAC service

    Returns:
        list[dict]: Monitoring rules

    Raises:
        HTTPException: 403 if not a member
    """
    await rbac.validate_workspace_access(current_user.id, organization_id)

    rules = await monitoring_service.get_organization_rules(
        organization_id,
        enabled_only=enabled_only,
    )

    return [
        {
            "id": rule.id,
            "name": rule.name,
            "program_id": rule.program_id,
            "frequency": rule.frequency,
            "enabled": rule.enabled,
            "last_run_at": rule.last_run_at,
            "last_run_status": rule.last_run_status,
            "created_at": rule.created_at,
        }
        for rule in rules
    ]


@router.get(
    "/rules/{rule_id}",
    summary="Get monitoring rule details",
    description="Get detailed information about a monitoring rule",
)
async def get_monitoring_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    rbac: RBACService = Depends(get_rbac_service),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get monitoring rule details.

    Args:
        rule_id: Monitoring rule ID
        current_user: Current authenticated user
        monitoring_service: Monitoring service
        rbac: RBAC service
        db: Database session

    Returns:
        dict: Monitoring rule details

    Raises:
        HTTPException: 403 if not authorized, 404 if not found
    """
    rule = await monitoring_service.get_monitoring_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring rule not found",
        )

    # Verify access to organization
    await rbac.validate_workspace_access(current_user.id, rule.organization_id)

    stats = await monitoring_service.get_rule_execution_stats(rule_id)

    return stats


@router.put(
    "/rules/{rule_id}",
    summary="Update monitoring rule",
    description="Update monitoring rule settings",
)
async def update_monitoring_rule(
    rule_id: UUID,
    name: str | None = None,
    frequency: str | None = None,
    description: str | None = None,
    enabled: bool | None = None,
    current_user: User = Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    """
    Update monitoring rule settings.

    Only organization members can update rules.

    Args:
        rule_id: Monitoring rule ID
        name: New rule name
        frequency: New frequency
        description: New description
        enabled: Enable/disable rule
        current_user: Current authenticated user
        monitoring_service: Monitoring service
        rbac: RBAC service

    Returns:
        dict: Updated rule

    Raises:
        HTTPException: 403 if not authorized, 404 if not found
    """
    rule = await monitoring_service.get_monitoring_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring rule not found",
        )

    await rbac.validate_workspace_access(current_user.id, rule.organization_id)

    try:
        updated_rule = await monitoring_service.update_monitoring_rule(
            rule_id=rule_id,
            name=name,
            frequency=frequency,
            description=description,
            enabled=enabled,
        )

        return {
            "id": updated_rule.id,
            "name": updated_rule.name,
            "frequency": updated_rule.frequency,
            "description": updated_rule.description,
            "enabled": updated_rule.enabled,
            "updated_at": updated_rule.updated_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete monitoring rule",
    description="Delete a monitoring rule",
)
async def delete_monitoring_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> None:
    """
    Delete a monitoring rule.

    Only organization members can delete rules.

    Args:
        rule_id: Monitoring rule ID
        current_user: Current authenticated user
        monitoring_service: Monitoring service
        rbac: RBAC service

    Raises:
        HTTPException: 403 if not authorized, 404 if not found
    """
    rule = await monitoring_service.get_monitoring_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring rule not found",
        )

    await rbac.validate_workspace_access(current_user.id, rule.organization_id)

    await monitoring_service.delete_monitoring_rule(rule_id)


@router.post(
    "/rules/{rule_id}/run",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Manually trigger monitoring rule",
    description="Manually execute a monitoring rule immediately",
)
async def trigger_monitoring_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    recon_service: ReconPipelineService = Depends(get_recon_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    """
    Manually trigger a monitoring rule execution.

    Immediately queues a recon scan for this rule.

    Args:
        rule_id: Monitoring rule ID
        current_user: Current authenticated user
        monitoring_service: Monitoring service
        recon_service: Recon pipeline service
        rbac: RBAC service

    Returns:
        dict: Queued scan info

    Raises:
        HTTPException: 403 if not authorized, 404 if not found
    """
    rule = await monitoring_service.get_monitoring_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring rule not found",
        )

    await rbac.validate_workspace_access(current_user.id, rule.organization_id)

    # Check permission to run scans
    await rbac.check_permission(
        current_user.id,
        rule.organization_id,
        Permission.RUN_SCANS,
    )

    try:
        # Create scan
        scan = await recon_service.create_scan(
            program_id=rule.program_id,
            scan_type="recon",
            created_by_id=current_user.id,
        )

        # Queue recon pipeline
        job = await recon_service.queue_recon_pipeline(
            program_id=rule.program_id,
            scan_id=scan.id,
            monitoring_rule_id=rule_id,
        )

        return {
            "status": "queued",
            "scan_id": str(scan.id),
            "job_id": job.job_id,
            "message": "Scan queued for execution",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to queue scan: {str(e)}",
        )


# ============================================================================
# OBSERVABILITY ENDPOINTS
# ============================================================================


@router.get(
    "/health",
    summary="Get platform health summary",
    description="Get org-isolated platform health across system, workers, Redis, and websocket telemetry",
)
async def get_platform_health(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    return await monitoring_service.generate_health_summary(organization_id)


@router.get(
    "/metrics",
    summary="Get platform metrics",
    description="Get org-scoped monitoring metrics and Prometheus exposition text",
)
async def get_platform_metrics(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    summary = await monitoring_service.monitor_platform_health(organization_id)
    return {
        "organization_id": str(organization_id),
        "health_score": summary["health_score"],
        "metrics": summary.get("metrics", {}),
        "prometheus": summary.get("prometheus", ""),
        "system": summary.get("system", {}),
        "redis": summary.get("redis", {}),
    }


@router.get(
    "/workers",
    summary="Get worker telemetry",
    description="Get distributed worker telemetry and bottleneck analysis",
)
async def get_worker_telemetry(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    return await monitoring_service.get_worker_telemetry(organization_id)


@router.get(
    "/ai",
    summary="Get AI telemetry",
    description="Get AI token usage, latency, cache hit rate, and provider health",
)
async def get_ai_telemetry(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    return await monitoring_service.get_ai_telemetry(organization_id)


@router.get(
    "/websocket",
    summary="Get websocket telemetry",
    description="Get websocket connection health, reconnects, and event delivery visibility",
)
async def get_websocket_telemetry(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    return await monitoring_service.get_websocket_telemetry(organization_id)


# ============================================================================
# ALERTS ENDPOINTS
# ============================================================================


@router.get(
    "/alerts",
    summary="List organization alerts",
    description="Get alerts for an organization",
)
async def list_alerts(
    organization_id: UUID,
    unacknowledged_only: bool = Query(False),
    severity: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> list[dict]:
    """
    List alerts for an organization.

    Args:
        organization_id: Organization ID
        unacknowledged_only: Only unacknowledged alerts
        severity: Filter by severity
        limit: Maximum results
        current_user: Current authenticated user
        alert_service: Alert service
        rbac: RBAC service

    Returns:
        list[dict]: Organization alerts

    Raises:
        HTTPException: 403 if not a member
    """
    await rbac.validate_workspace_access(current_user.id, organization_id)

    alerts = await alert_service.get_organization_alerts(
        organization_id,
        unacknowledged_only=unacknowledged_only,
        severity=severity,
        limit=limit,
    )

    return [
        {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "description": alert.description,
            "is_acknowledged": alert.is_acknowledged,
            "created_at": alert.created_at,
        }
        for alert in alerts
    ]


@router.get(
    "/alerts/{alert_id}",
    summary="Get alert details",
    description="Get detailed information about an alert",
)
async def get_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    """Get alert details."""
    alert = await alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    await rbac.validate_workspace_access(current_user.id, alert.organization_id)

    return {
        "id": alert.id,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "title": alert.title,
        "description": alert.description,
        "delta_data": alert.delta_data,
        "is_acknowledged": alert.is_acknowledged,
        "acknowledged_at": alert.acknowledged_at,
        "created_at": alert.created_at,
    }


@router.post(
    "/alerts/{alert_id}/acknowledge",
    summary="Acknowledge alert",
    description="Mark an alert as acknowledged",
)
async def acknowledge_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    """Acknowledge an alert."""
    alert = await alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    await rbac.validate_workspace_access(current_user.id, alert.organization_id)

    acknowledged = await alert_service.acknowledge_alert(
        alert_id=alert_id,
        acknowledged_by_id=current_user.id,
    )

    return {
        "id": acknowledged.id,
        "is_acknowledged": acknowledged.is_acknowledged,
        "acknowledged_at": acknowledged.acknowledged_at,
    }


@router.get(
    "/summary",
    summary="Get monitoring summary",
    description="Get alert summary statistics",
)
async def get_monitoring_summary(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    """Get monitoring summary for organization."""
    await rbac.validate_workspace_access(current_user.id, organization_id)

    summary = await alert_service.get_alert_summary(organization_id)
    return summary
