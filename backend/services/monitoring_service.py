"""
Monitoring service for continuous recon automation.
Manages recurring scan rules, execution, and lifecycle management.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from uuid import UUID
from typing import Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.cluster.worker_registry import WorkerRegistry
from backend.core.redis import get_redis
from backend.metrics.prometheus_metrics import prometheus_metrics
from backend.metrics.system_metrics import collect_system_metrics, summarize_system_health, detect_resource_pressure
from backend.observability.logger import get_structured_logger
from backend.observability.metrics_collector import aggregate_metrics, emit_metric_event, record_metric
from backend.telemetry.ai_telemetry import detect_provider_failures, monitor_ai_latency, track_token_usage
from backend.telemetry.websocket_telemetry import detect_connection_issues, monitor_connection_health, track_event_delivery
from backend.telemetry.worker_telemetry import detect_worker_bottlenecks, monitor_task_execution, track_worker_load

from backend.models.monitoring_rule import MonitoringRule, MonitoringFrequency
from backend.models.program import Program
from backend.models.scan import Scan, ScanStatus
from backend.models.worker_node import WorkerNode
from backend.models.cluster_job import ClusterJob
from backend.health.worker_health import WorkerHealth
from backend.core.events import EventType
from backend.services.event_service import event_service

logger = get_structured_logger(__name__)


class MonitoringService:
    """Service for monitoring rule management and execution."""

    def __init__(self, db: AsyncSession):
        """Initialize monitoring service with database session."""
        self.db = db
        self.worker_health = WorkerHealth()
        self.worker_registry = WorkerRegistry(db)

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

    # ---------------------------------------------------------------------
    # Observability / telemetry
    # ---------------------------------------------------------------------

    async def generate_health_summary(self, organization_id: UUID) -> dict[str, Any]:
        """Generate a sanitized org-scoped platform health snapshot."""
        system = summarize_system_health()
        resources = collect_system_metrics()

        worker_result = await self.db.execute(
            select(WorkerNode).where(WorkerNode.organization_id == str(organization_id))
        )
        workers = worker_result.scalars().all()
        worker_overview = await track_worker_load(workers)
        worker_bottlenecks = detect_worker_bottlenecks(workers)

        job_result = await self.db.execute(
            select(ClusterJob).where(ClusterJob.organization_id == str(organization_id))
        )
        jobs = job_result.scalars().all()
        redis_state = await self._inspect_redis_state(str(organization_id))
        websocket_state = await monitor_connection_health(str(organization_id))
        websocket_issues = await detect_connection_issues(str(organization_id))

        metrics_snapshot = await aggregate_metrics(str(organization_id))

        health_score = self._calculate_platform_health_score(
            system_health=system,
            worker_overview=worker_overview,
            redis_state=redis_state,
            websocket_state=websocket_state,
            job_count=len(jobs),
        )

        summary = {
            "organization_id": str(organization_id),
            "status": "degraded" if health_score < 0.7 else "healthy",
            "health_score": health_score,
            "system": system,
            "resources": resources,
            "redis": redis_state,
            "workers": worker_overview,
            "worker_bottlenecks": worker_bottlenecks,
            "jobs": {
                "queued": sum(1 for job in jobs if job.status == "queued"),
                "running": sum(1 for job in jobs if job.status in {"assigned", "running"}),
                "failed": sum(1 for job in jobs if job.status == "failed"),
                "total": len(jobs),
            },
            "websocket": websocket_state,
            "websocket_issues": websocket_issues,
            "metrics": metrics_snapshot,
            "resource_pressure": detect_resource_pressure(resources),
        }

        await emit_metric_event(
            "platform.health_score",
            health_score,
            organization_id=str(organization_id),
            labels={"status": summary["status"]},
        )
        await event_service.emit_event(
            EventType.MONITORING_HEALTH_UPDATED,
            str(organization_id),
            {"health_score": health_score, "status": summary["status"]},
        )
        logger.info("Generated health summary for org %s", organization_id)
        return summary

    async def monitor_platform_health(self, organization_id: UUID) -> dict[str, Any]:
        """Aggregate telemetry and export Prometheus-compatible metrics."""
        summary = await self.generate_health_summary(organization_id)
        prometheus_text = await prometheus_metrics.render_metrics_text(str(organization_id), summary)
        summary["prometheus"] = prometheus_text
        return summary

    async def detect_platform_degradation(self, organization_id: UUID) -> dict[str, Any]:
        """Detect cross-domain platform degradation signals."""
        health = await self.generate_health_summary(organization_id)
        issues: list[dict[str, Any]] = []

        if health["health_score"] < 0.65:
            issues.append({"area": "platform", "issue": "low_health_score", "severity": "high"})
        if health["redis"]["healthy"] is False:
            issues.append({"area": "redis", "issue": "redis_unhealthy", "severity": "critical"})
        if health["websocket"]["healthy"] is False:
            issues.append({"area": "websocket", "issue": "connection_issues", "severity": "high"})
        if health["worker_bottlenecks"]:
            issues.extend(health["worker_bottlenecks"])
        if health["resource_pressure"]:
            issues.extend([{**item, "area": "system"} for item in health["resource_pressure"]])

        return {
            "organization_id": str(organization_id),
            "degraded": bool(issues),
            "issues": issues,
            "health": health,
        }

    async def get_worker_telemetry(self, organization_id: UUID) -> dict[str, Any]:
        """Return org-scoped worker telemetry details."""
        summary = await self.generate_health_summary(organization_id)
        return {
            "organization_id": str(organization_id),
            "workers": summary.get("workers", {}),
            "worker_bottlenecks": summary.get("worker_bottlenecks", []),
            "jobs": summary.get("jobs", {}),
        }

    async def get_websocket_telemetry(self, organization_id: UUID) -> dict[str, Any]:
        """Return org-scoped websocket telemetry details."""
        summary = await self.generate_health_summary(organization_id)
        return {
            "organization_id": str(organization_id),
            "websocket": summary.get("websocket", {}),
            "issues": summary.get("websocket_issues", []),
            "recent_events": summary.get("metrics", {}).get("recent_events", []),
        }

    async def get_ai_telemetry(self, organization_id: UUID) -> dict[str, Any]:
        """Return org-scoped AI telemetry details."""
        from backend.telemetry.ai_telemetry import summarize_ai_metrics

        return summarize_ai_metrics(str(organization_id))

    async def _aggregate_ai_token_usage(self, organization_id: str) -> dict[str, Any]:
        return (await self.get_ai_telemetry(UUID(organization_id))).get("token_usage", {})

    async def _aggregate_ai_latency(self, organization_id: str) -> dict[str, Any]:
        return (await self.get_ai_telemetry(UUID(organization_id))).get("latency", {})

    async def _aggregate_ai_provider_health(self, organization_id: str) -> list[dict[str, Any]]:
        return (await self.get_ai_telemetry(UUID(organization_id))).get("provider_health", [])

    async def _inspect_redis_state(self, organization_id: str) -> dict[str, Any]:
        redis_client = await get_redis()
        healthy = True
        queue_depth = 0
        stream_length = 0
        try:
            healthy = bool(await redis_client.ping())
            queue_depth = int(await redis_client.zcard(f"cluster_jobs:{organization_id}"))
            stream_length = int(await redis_client.xlen(event_service.STREAM_NAME))
        except Exception as exc:
            healthy = False
            logger.warning("Redis health inspection failed for org %s: %s", organization_id, exc)

        return {
            "healthy": healthy,
            "queue_depth": queue_depth,
            "event_stream_length": stream_length,
        }

    def _calculate_platform_health_score(
        self,
        system_health: dict[str, Any],
        worker_overview: dict[str, Any],
        redis_state: dict[str, Any],
        websocket_state: dict[str, Any],
        job_count: int,
    ) -> float:
        score = 1.0
        score -= min(0.35, system_health.get("pressure_score", 0.0) * 0.35)
        score -= min(0.2, max(0, worker_overview.get("failed_workers", 0)) * 0.05)
        score -= 0.15 if not redis_state.get("healthy", True) else 0.0
        score -= 0.15 if not websocket_state.get("healthy", True) else 0.0
        score -= min(0.15, max(0, job_count - 25) * 0.005)
        return round(max(0.0, min(1.0, score)), 3)

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
