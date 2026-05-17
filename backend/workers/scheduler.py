"""
Monitoring scheduler worker for continuous recon automation.
Executes recurring monitoring rules at specified intervals via ARQ.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.session import get_db
from backend.services.monitoring_service import MonitoringService
from backend.services.recon_pipeline_service import ReconPipelineService
from backend.services.delta_service import DeltaService
from backend.services.alert_service import AlertService
from backend.models.scan import ScanStatus

logger = logging.getLogger(__name__)


async def execute_monitoring_scheduler(
    db: Optional[AsyncSession] = None,
) -> dict:
    """
    Main scheduler task to execute due monitoring rules.

    This task runs periodically (e.g., every 5 minutes) to check which
    monitoring rules are due for execution and dispatch them to the queue.

    Args:
        db: Database session (optional, uses default if None)

    Returns:
        dict: Execution summary
    """
    if db is None:
        db = get_db()

    monitoring_service = MonitoringService(db)
    recon_service = ReconPipelineService(db)

    try:
        # Get all due monitoring rules
        due_rules = await monitoring_service.get_due_monitoring_rules()

        logger.info(f"Found {len(due_rules)} due monitoring rules to execute")

        executed_count = 0
        failed_count = 0

        for rule in due_rules:
            try:
                # Execute the monitoring rule
                success = await execute_monitoring_rule(
                    rule_id=rule.id,
                    program_id=rule.program_id,
                    organization_id=rule.organization_id,
                    db=db,
                )

                if success:
                    executed_count += 1
                    logger.info(f"Successfully executed monitoring rule {rule.id}")
                else:
                    failed_count += 1
                    logger.warning(f"Failed to execute monitoring rule {rule.id}")

            except Exception as e:
                failed_count += 1
                logger.exception(f"Error executing monitoring rule {rule.id}: {e}")

        return {
            "status": "completed",
            "due_rules_found": len(due_rules),
            "executed_count": executed_count,
            "failed_count": failed_count,
        }

    except Exception as e:
        logger.exception(f"Error in monitoring scheduler: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


async def execute_monitoring_rule(
    rule_id: UUID,
    program_id: UUID,
    organization_id: UUID,
    db: AsyncSession,
) -> bool:
    """
    Execute a single monitoring rule.

    Dispatches a recon scan job to the queue and records the execution.

    Args:
        rule_id: Monitoring rule ID
        program_id: Program to scan
        organization_id: Organization context
        db: Database session

    Returns:
        bool: True if execution was successful
    """
    monitoring_service = MonitoringService(db)
    recon_service = ReconPipelineService(db)

    try:
        # Create a scan for this monitoring rule
        scan = await recon_service.create_scan(
            program_id=program_id,
            scan_type="recon",
            created_by_id=None,
        )

        logger.info(f"Created scan {scan.id} for monitoring rule {rule_id}")

        # Dispatch scan to queue
        job = await recon_service.queue_recon_pipeline(
            program_id=program_id,
            scan_id=scan.id,
            monitoring_rule_id=rule_id,
        )

        logger.info(f"Queued recon pipeline job {job.job_id} for scan {scan.id}")

        # Record rule execution
        await monitoring_service.record_rule_execution(
            rule_id=rule_id,
            scan_id=scan.id,
            status="queued",
        )

        return True

    except Exception as e:
        logger.exception(f"Error executing monitoring rule {rule_id}: {e}")
        # Record failed execution
        try:
            await monitoring_service.record_rule_execution(
                rule_id=rule_id,
                scan_id=None,
                status="failed",
            )
        except Exception as record_e:
            logger.exception(f"Failed to record rule execution: {record_e}")
        return False


async def process_monitoring_scan_completion(
    scan_id: UUID,
    program_id: UUID,
    organization_id: UUID,
    monitoring_rule_id: Optional[UUID] = None,
    db: Optional[AsyncSession] = None,
) -> dict:
    """
    Process a completed monitoring scan and generate alerts.

    This task runs after a recon scan completes when triggered by a monitoring rule.
    Performs delta analysis and creates appropriate alerts.

    Args:
        scan_id: Completed scan ID
        program_id: Program ID
        organization_id: Organization ID
        monitoring_rule_id: Associated monitoring rule (optional)
        db: Database session

    Returns:
        dict: Processing summary
    """
    if db is None:
        from backend.database.session import get_db
        db = await get_db()

    delta_service = DeltaService(db)
    alert_service = AlertService(db)
    monitoring_service = MonitoringService(db)

    try:
        logger.info(f"Processing monitoring scan completion for scan {scan_id}")

        # Generate delta analysis
        delta = await delta_service.generate_delta_report(
            program_id=program_id,
            current_scan_id=scan_id,
        )

        logger.info(f"Delta analysis complete: {delta.summary}")

        alerts_created = 0

        # Create alerts for new assets
        for asset in delta.new_assets:
            alert = await alert_service.create_new_asset_alert(
                organization_id=organization_id,
                program_id=program_id,
                scan_id=scan_id,
                monitoring_rule_id=monitoring_rule_id,
                asset_hostname=asset.get("hostname", "unknown"),
                asset_ip=asset.get("ip_address"),
            )
            alerts_created += 1
            logger.info(f"Created new asset alert {alert.id}")

        # Create alerts for new critical/high findings
        for finding in delta.critical_findings:
            alert = await alert_service.create_new_finding_alert(
                organization_id=organization_id,
                program_id=program_id,
                scan_id=scan_id,
                monitoring_rule_id=monitoring_rule_id,
                finding_title=finding.get("title", "unknown"),
                finding_severity=finding.get("severity", "medium"),
                endpoint=finding.get("endpoint"),
            )
            alerts_created += 1
            logger.info(f"Created finding alert {alert.id}")

        # Create scan completion alert with summary
        if delta.summary.get("has_significant_changes"):
            alert = await alert_service.create_scan_completed_alert(
                organization_id=organization_id,
                program_id=program_id,
                scan_id=scan_id,
                monitoring_rule_id=monitoring_rule_id,
                new_findings_count=delta.summary.get("new_findings_count", 0),
                new_assets_count=delta.summary.get("new_assets_count", 0),
            )
            alerts_created += 1
            logger.info(f"Created scan completion alert {alert.id}")

        # Update rule execution status if associated
        if monitoring_rule_id:
            await monitoring_service.record_rule_execution(
                rule_id=monitoring_rule_id,
                scan_id=scan_id,
                status="completed",
            )
            logger.info(f"Updated monitoring rule {monitoring_rule_id} execution status")

        return {
            "status": "completed",
            "scan_id": str(scan_id),
            "alerts_created": alerts_created,
            "delta_summary": delta.summary,
        }

    except Exception as e:
        logger.exception(f"Error processing monitoring scan completion: {e}")
        return {
            "status": "error",
            "scan_id": str(scan_id),
            "error": str(e),
        }


async def check_monitoring_queue_health(
    db: Optional[AsyncSession] = None,
) -> dict:
    """
    Health check for monitoring system.

    Verifies that the monitoring scheduler and queue are functioning properly.

    Args:
        db: Database session

    Returns:
        dict: Health check results
    """
    if db is None:
        from backend.database.session import get_db
        db = await get_db()

    monitoring_service = MonitoringService(db)

    try:
        # Get count of enabled rules
        rules = await monitoring_service.get_organization_rules(
            organization_id=None,
            enabled_only=True,
        )
        enabled_rules_count = len(rules)

        # Get count of due rules
        due_rules = await monitoring_service.get_due_monitoring_rules()
        due_count = len(due_rules)

        return {
            "status": "healthy",
            "enabled_rules_count": enabled_rules_count,
            "due_rules_count": due_count,
            "scheduler_active": True,
        }

    except Exception as e:
        logger.exception(f"Error in monitoring health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }
