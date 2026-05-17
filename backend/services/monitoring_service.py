"""
Monitoring service for continuous recon automation.
Manages recurring scan rules, execution, and lifecycle management.
"""
from __future__ import annotations

from uuid import UUID
from typing import Optional
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.models.monitoring_rule import MonitoringRule, MonitoringFrequency
from backend.models.program import Program
from backend.models.scan import Scan, ScanStatus


class MonitoringService:
    """Service for monitoring rule management and execution."""

    def __init__(self, db: AsyncSession):
        """Initialize monitoring service with database session."""
        self.db = db

    # Frequency mappings in seconds
    FREQUENCY_INTERVALS = {
        MonitoringFrequency.HOURLY: 3600,
        MonitoringFrequency.DAILY: 86400,
        MonitoringFrequency.WEEKLY: 604800,
    }

    async def create_monitoring_rule(
        self,
        organization_id: UUID,
        program_id: UUID,
        name: str,
        frequency: str = MonitoringFrequency.DAILY,
        description: Optional[str] = None,
        created_by_id: Optional[UUID] = None,
    ) -> MonitoringRule:
        """
        Create a new monitoring rule for automated recurring scans.

        Args:
            organization_id: Organization that owns the rule
            program_id: Program to monitor
            name: Rule name
            frequency: Scan frequency (hourly, daily, weekly)
            description: Optional description
            created_by_id: User creating the rule

        Returns:
            MonitoringRule: Created monitoring rule

        Raises:
            HTTPException: If validation fails
        """
        # Validate frequency
        if frequency not in [f.value for f in MonitoringFrequency]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid frequency. Must be one of: {[f.value for f in MonitoringFrequency]}",
            )

        # Verify program exists and belongs to organization
        result = await self.db.execute(
            select(Program).where(
                and_(
                    Program.id == program_id,
                    Program.organization_id == organization_id,
                )
            )
        )
        if not result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Program not found in this organization",
            )

        rule = MonitoringRule(
            organization_id=organization_id,
            program_id=program_id,
            name=name,
            frequency=frequency,
            description=description,
            created_by_id=created_by_id,
            enabled=True,
            is_active=True,
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def get_monitoring_rule(self, rule_id: UUID) -> Optional[MonitoringRule]:
        """Get monitoring rule by ID."""
        result = await self.db.execute(
            select(MonitoringRule).where(MonitoringRule.id == rule_id)
        )
        return result.scalars().first()

    async def get_organization_rules(
        self,
        organization_id: UUID,
        enabled_only: bool = False,
    ) -> list[MonitoringRule]:
        """
        Get all monitoring rules for an organization.

        Args:
            organization_id: Organization ID
            enabled_only: Only return enabled rules

        Returns:
            list[MonitoringRule]: Monitoring rules
        """
        query = select(MonitoringRule).where(
            MonitoringRule.organization_id == organization_id
        )
        if enabled_only:
            query = query.where(MonitoringRule.enabled == True)
        
        query = query.order_by(MonitoringRule.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_program_rules(
        self,
        program_id: UUID,
        organization_id: UUID,
    ) -> list[MonitoringRule]:
        """Get all monitoring rules for a specific program."""
        result = await self.db.execute(
            select(MonitoringRule).where(
                and_(
                    MonitoringRule.program_id == program_id,
                    MonitoringRule.organization_id == organization_id,
                )
            ).order_by(MonitoringRule.created_at.desc())
        )
        return result.scalars().all()

    async def update_monitoring_rule(
        self,
        rule_id: UUID,
        name: Optional[str] = None,
        frequency: Optional[str] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> MonitoringRule:
        """Update monitoring rule settings."""
        rule = await self.get_monitoring_rule(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Monitoring rule not found",
            )

        if frequency and frequency not in [f.value for f in MonitoringFrequency]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid frequency. Must be one of: {[f.value for f in MonitoringFrequency]}",
            )

        if name is not None:
            rule.name = name
        if frequency is not None:
            rule.frequency = frequency
        if description is not None:
            rule.description = description
        if enabled is not None:
            rule.enabled = enabled

        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def delete_monitoring_rule(self, rule_id: UUID) -> None:
        """Delete a monitoring rule."""
        rule = await self.get_monitoring_rule(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Monitoring rule not found",
            )

        await self.db.delete(rule)
        await self.db.commit()

    async def should_execute_rule(self, rule: MonitoringRule) -> bool:
        """
        Check if a monitoring rule should be executed based on frequency.

        Args:
            rule: Monitoring rule to check

        Returns:
            bool: True if rule should execute now
        """
        if not rule.enabled or not rule.is_active:
            return False

        # First run should always execute
        if rule.last_run_at is None:
            return True

        # Check if enough time has passed based on frequency
        interval_seconds = self.FREQUENCY_INTERVALS.get(
            MonitoringFrequency(rule.frequency), 86400
        )
        next_run_time = rule.last_run_at + timedelta(seconds=interval_seconds)
        
        return datetime.now(rule.last_run_at.tzinfo) >= next_run_time

    async def get_due_monitoring_rules(
        self,
        organization_id: Optional[UUID] = None,
    ) -> list[MonitoringRule]:
        """
        Get all monitoring rules that are due for execution.

        Args:
            organization_id: Filter by organization (optional)

        Returns:
            list[MonitoringRule]: Rules that should execute now
        """
        query = select(MonitoringRule).where(
            and_(
                MonitoringRule.enabled == True,
                MonitoringRule.is_active == True,
            )
        )

        if organization_id:
            query = query.where(MonitoringRule.organization_id == organization_id)

        result = await self.db.execute(query)
        all_rules = result.scalars().all()

        # Filter to only due rules
        due_rules = []
        for rule in all_rules:
            if await self.should_execute_rule(rule):
                due_rules.append(rule)

        return due_rules

    async def record_rule_execution(
        self,
        rule_id: UUID,
        scan_id: UUID,
        status: str = "completed",
    ) -> MonitoringRule:
        """
        Record that a monitoring rule has been executed.

        Args:
            rule_id: Monitoring rule ID
            scan_id: Associated scan ID
            status: Execution status

        Returns:
            MonitoringRule: Updated rule
        """
        rule = await self.get_monitoring_rule(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Monitoring rule not found",
            )

        rule.last_run_at = datetime.now(datetime.now().astimezone().tzinfo)
        rule.last_run_status = status

        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def get_rule_execution_stats(self, rule_id: UUID) -> dict:
        """Get execution statistics for a monitoring rule."""
        rule = await self.get_monitoring_rule(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Monitoring rule not found",
            )

        return {
            "rule_id": rule.id,
            "name": rule.name,
            "frequency": rule.frequency,
            "enabled": rule.enabled,
            "last_run_at": rule.last_run_at,
            "last_run_status": rule.last_run_status,
            "created_at": rule.created_at,
            "next_expected_run": self._calculate_next_run(rule),
        }

    def _calculate_next_run(self, rule: MonitoringRule) -> Optional[datetime]:
        """Calculate when rule should next execute."""
        if not rule.enabled or not rule.is_active:
            return None

        if rule.last_run_at is None:
            return datetime.now(datetime.now().astimezone().tzinfo)

        interval_seconds = self.FREQUENCY_INTERVALS.get(
            MonitoringFrequency(rule.frequency), 86400
        )
        return rule.last_run_at + timedelta(seconds=interval_seconds)
