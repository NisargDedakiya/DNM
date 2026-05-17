"""
Alert service for monitoring-driven notifications.
Manages alert generation, deduplication, and real-time delivery.
"""
from __future__ import annotations

from uuid import UUID
from typing import Optional
from datetime import datetime, timedelta
import json

from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.models.alert import Alert, AlertType, AlertSeverity
from backend.models.monitoring_rule import MonitoringRule
from backend.models.scan import Scan


class AlertService:
    """Service for alert management and deduplication."""

    def __init__(self, db: AsyncSession):
        """Initialize alert service with database session."""
        self.db = db

    # Deduplication window: 1 hour
    DEDUP_WINDOW_SECONDS = 3600

    async def create_alert(
        self,
        organization_id: UUID,
        program_id: UUID,
        alert_type: str,
        title: str,
        description: str,
        severity: str = AlertSeverity.MEDIUM,
        monitoring_rule_id: Optional[UUID] = None,
        scan_id: Optional[UUID] = None,
        delta_data: Optional[dict] = None,
    ) -> Alert:
        """
        Create a new alert, checking for duplicates first.

        Args:
            organization_id: Organization ID
            program_id: Program ID
            alert_type: Type of alert
            title: Alert title
            description: Alert description
            severity: Alert severity
            monitoring_rule_id: Associated monitoring rule
            scan_id: Associated scan
            delta_data: Delta data JSON

        Returns:
            Alert: Created alert (or existing duplicate)
        """
        # Check for recent duplicate
        duplicate = await self._find_duplicate_alert(
            organization_id,
            program_id,
            alert_type,
            title,
        )

        if duplicate:
            # Return existing alert instead of creating duplicate
            return duplicate

        # Create new alert
        delta_json = json.dumps(delta_data) if delta_data else None

        alert = Alert(
            organization_id=organization_id,
            program_id=program_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            monitoring_rule_id=monitoring_rule_id,
            scan_id=scan_id,
            delta_data=delta_json,
            is_duplicate=False,
            is_acknowledged=False,
        )

        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def _find_duplicate_alert(
        self,
        organization_id: UUID,
        program_id: UUID,
        alert_type: str,
        title: str,
    ) -> Optional[Alert]:
        """
        Find a recent identical alert to prevent duplicates.

        Args:
            organization_id: Organization ID
            program_id: Program ID
            alert_type: Alert type
            title: Alert title

        Returns:
            Alert or None if no duplicate found
        """
        cutoff_time = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(
            seconds=self.DEDUP_WINDOW_SECONDS
        )

        result = await self.db.execute(
            select(Alert).where(
                and_(
                    Alert.organization_id == organization_id,
                    Alert.program_id == program_id,
                    Alert.alert_type == alert_type,
                    Alert.title == title,
                    Alert.created_at >= cutoff_time,
                    Alert.is_duplicate == False,
                )
            ).order_by(desc(Alert.created_at)).limit(1)
        )
        return result.scalars().first()

    async def get_alert(self, alert_id: UUID) -> Optional[Alert]:
        """Get alert by ID."""
        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        return result.scalars().first()

    async def get_organization_alerts(
        self,
        organization_id: UUID,
        unacknowledged_only: bool = False,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> list[Alert]:
        """
        Get alerts for an organization.

        Args:
            organization_id: Organization ID
            unacknowledged_only: Only return unacknowledged alerts
            severity: Filter by severity level
            limit: Maximum results

        Returns:
            list[Alert]: Organization alerts
        """
        query = select(Alert).where(Alert.organization_id == organization_id)

        if unacknowledged_only:
            query = query.where(Alert.is_acknowledged == False)

        if severity:
            query = query.where(Alert.severity == severity)

        query = query.order_by(desc(Alert.created_at)).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_program_alerts(
        self,
        program_id: UUID,
        organization_id: UUID,
        limit: int = 50,
    ) -> list[Alert]:
        """Get alerts for a specific program."""
        result = await self.db.execute(
            select(Alert).where(
                and_(
                    Alert.program_id == program_id,
                    Alert.organization_id == organization_id,
                )
            ).order_by(desc(Alert.created_at)).limit(limit)
        )
        return result.scalars().all()

    async def acknowledge_alert(
        self,
        alert_id: UUID,
        acknowledged_by_id: UUID,
    ) -> Alert:
        """Acknowledge an alert."""
        alert = await self.get_alert(alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found",
            )

        alert.is_acknowledged = True
        alert.acknowledged_at = datetime.now(datetime.now().astimezone().tzinfo)
        alert.acknowledged_by_id = acknowledged_by_id

        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def mark_as_duplicate(
        self,
        alert_id: UUID,
        parent_alert_id: UUID,
    ) -> Alert:
        """Mark an alert as a duplicate of another."""
        alert = await self.get_alert(alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found",
            )

        alert.is_duplicate = True
        alert.parent_alert_id = parent_alert_id

        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def get_critical_alerts(
        self,
        organization_id: UUID,
        unacknowledged_only: bool = True,
    ) -> list[Alert]:
        """Get all critical/high severity unacknowledged alerts."""
        query = select(Alert).where(
            and_(
                Alert.organization_id == organization_id,
                Alert.severity.in_([AlertSeverity.CRITICAL, AlertSeverity.HIGH]),
            )
        )

        if unacknowledged_only:
            query = query.where(Alert.is_acknowledged == False)

        query = query.order_by(desc(Alert.created_at))

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_alert_summary(self, organization_id: UUID) -> dict:
        """Get summary statistics for organization alerts."""
        # Total alerts
        result = await self.db.execute(
            select(Alert).where(Alert.organization_id == organization_id)
        )
        total_alerts = len(result.scalars().all())

        # Unacknowledged
        result = await self.db.execute(
            select(Alert).where(
                and_(
                    Alert.organization_id == organization_id,
                    Alert.is_acknowledged == False,
                )
            )
        )
        unacknowledged = len(result.scalars().all())

        # Critical/High
        result = await self.db.execute(
            select(Alert).where(
                and_(
                    Alert.organization_id == organization_id,
                    Alert.severity.in_([AlertSeverity.CRITICAL, AlertSeverity.HIGH]),
                )
            )
        )
        critical_high = len(result.scalars().all())

        # By type
        alert_types = {}
        for alert_type in AlertType:
            result = await self.db.execute(
                select(Alert).where(
                    and_(
                        Alert.organization_id == organization_id,
                        Alert.alert_type == alert_type.value,
                    )
                )
            )
            alert_types[alert_type.value] = len(result.scalars().all())

        return {
            "total_alerts": total_alerts,
            "unacknowledged_count": unacknowledged,
            "critical_high_count": critical_high,
            "by_type": alert_types,
        }

    async def create_new_asset_alert(
        self,
        organization_id: UUID,
        program_id: UUID,
        scan_id: UUID,
        monitoring_rule_id: Optional[UUID],
        asset_hostname: str,
        asset_ip: Optional[str],
    ) -> Alert:
        """Create alert for newly discovered asset."""
        return await self.create_alert(
            organization_id=organization_id,
            program_id=program_id,
            alert_type=AlertType.NEW_ASSET,
            title=f"New asset discovered: {asset_hostname}",
            description=f"New asset {asset_hostname} ({asset_ip}) discovered during monitoring scan",
            severity=AlertSeverity.MEDIUM,
            monitoring_rule_id=monitoring_rule_id,
            scan_id=scan_id,
            delta_data={
                "hostname": asset_hostname,
                "ip_address": asset_ip,
            },
        )

    async def create_new_finding_alert(
        self,
        organization_id: UUID,
        program_id: UUID,
        scan_id: UUID,
        monitoring_rule_id: Optional[UUID],
        finding_title: str,
        finding_severity: str,
        endpoint: Optional[str],
    ) -> Alert:
        """Create alert for newly discovered finding."""
        # Determine alert severity from finding severity
        alert_severity = finding_severity
        if finding_severity == SeverityLevel.CRITICAL:
            alert_severity = AlertSeverity.CRITICAL
        elif finding_severity == SeverityLevel.HIGH:
            alert_severity = AlertSeverity.HIGH

        return await self.create_alert(
            organization_id=organization_id,
            program_id=program_id,
            alert_type=AlertType.NEW_FINDING,
            title=f"New finding: {finding_title}",
            description=f"{finding_severity.upper()} severity finding discovered: {finding_title} on {endpoint}",
            severity=alert_severity,
            monitoring_rule_id=monitoring_rule_id,
            scan_id=scan_id,
            delta_data={
                "title": finding_title,
                "severity": finding_severity,
                "endpoint": endpoint,
            },
        )

    async def create_scan_completed_alert(
        self,
        organization_id: UUID,
        program_id: UUID,
        scan_id: UUID,
        monitoring_rule_id: Optional[UUID],
        new_findings_count: int,
        new_assets_count: int,
    ) -> Alert:
        """Create alert for completed monitoring scan."""
        return await self.create_alert(
            organization_id=organization_id,
            program_id=program_id,
            alert_type=AlertType.SCAN_COMPLETED,
            title=f"Monitoring scan completed",
            description=f"Scan completed: {new_findings_count} new findings, {new_assets_count} new assets discovered",
            severity=AlertSeverity.INFO,
            monitoring_rule_id=monitoring_rule_id,
            scan_id=scan_id,
            delta_data={
                "new_findings": new_findings_count,
                "new_assets": new_assets_count,
            },
        )
