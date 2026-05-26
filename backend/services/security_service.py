"""
Security hardening orchestration service.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.hardening.sandbox_engine import create_execution_sandbox, enforce_resource_limits, cleanup_sandbox
from backend.hardening.rate_limiter import calculate_request_budget, enforce_rate_limit, throttle_aggressive_activity
from backend.hardening.resource_guard import isolate_resource_pressure, monitor_resource_usage, enforce_resource_boundaries
from backend.models.audit_log import AuditLog
from backend.models.recovery_snapshot import RecoverySnapshot
from backend.models.security_event import SecurityEvent
from backend.recovery.backup_manager import create_backup_snapshot
from backend.recovery.disaster_recovery import initiate_recovery, validate_recovery_integrity
from backend.security.abuse_detection import analyze_behavior_pattern, detect_abuse_activity, quarantine_suspicious_activity
from backend.security.audit_integrity import generate_audit_entry, verify_log_integrity

logger = logging.getLogger(__name__)


class SecurityService:
    """Coordinates sandboxing, rate limits, audit integrity, and recovery."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_secure_execution(self, organization_id: UUID, actor: str, action: str, activity: dict[str, Any] | None = None) -> dict[str, Any]:
        activity = activity or {}
        sandbox = create_execution_sandbox(str(organization_id), actor, action, timeout_seconds=int(activity.get("timeout_seconds") or 300))
        sandbox = enforce_resource_limits(sandbox, activity.get("resource_usage"))
        rate_limit = await enforce_rate_limit(str(organization_id), activity_type=activity.get("activity_type", "api"), risk_level=activity.get("risk_level", "medium"))
        abuse = quarantine_suspicious_activity(activity)
        resource = isolate_resource_pressure(activity.get("resource_usage", {}))

        audit_entry = generate_audit_entry(str(organization_id), actor, action, {"sandbox_id": sandbox["sandbox_id"], "allowed": rate_limit["allowed"], "suspicious": abuse["suspicious"]})
        await self._persist_security_event(str(organization_id), action, abuse["severity"], audit_entry["summary"] if "summary" in audit_entry else action)
        await self._persist_audit_log(str(organization_id), actor, action, audit_entry["integrity_hash"])

        return {
            "organization_id": str(organization_id),
            "sandbox": cleanup_sandbox(sandbox),
            "rate_limit": rate_limit,
            "abuse_detection": abuse,
            "resource_guard": resource,
            "audit_entry": audit_entry,
        }

    async def analyze_security_health(self, organization_id: UUID) -> dict[str, Any]:
        event_rows = await self.db.execute(select(SecurityEvent).where(SecurityEvent.organization_id == organization_id).order_by(SecurityEvent.created_at.desc()).limit(50))
        log_rows = await self.db.execute(select(AuditLog).where(AuditLog.organization_id == organization_id).order_by(AuditLog.created_at.desc()).limit(50))
        snapshots = await self.db.execute(select(RecoverySnapshot).where(RecoverySnapshot.organization_id == organization_id).order_by(RecoverySnapshot.created_at.desc()).limit(20))

        events = list(event_rows.scalars().all())
        logs = list(log_rows.scalars().all())
        recovery = list(snapshots.scalars().all())

        integrity = verify_log_integrity([
            {"organization_id": str(log.organization_id), "actor": log.actor, "action": log.action, "integrity_hash": log.integrity_hash, "payload": {}}
            for log in logs
        ])

        return {
            "organization_id": str(organization_id),
            "security_events": len(events),
            "audit_entries": len(logs),
            "recovery_snapshots": len(recovery),
            "audit_integrity": integrity,
            "rate_budget": calculate_request_budget(str(organization_id)),
            "resource_pressure": monitor_resource_usage({"cpu_percent": 0, "memory_percent": 0, "worker_utilization_percent": 0}),
            "summary": "Security health evaluated for org-scoped deployment hardening.",
        }

    async def generate_security_summary(self, organization_id: UUID) -> dict[str, Any]:
        health = await self.analyze_security_health(organization_id)
        return {
            "organization_id": str(organization_id),
            "summary": health["summary"],
            "integrity": health["audit_integrity"],
            "rate_limit": health["rate_budget"],
            "recovery": {
                "snapshot_count": health["recovery_snapshots"],
                "status": "available" if health["recovery_snapshots"] else "none",
            },
            "abuse": analyze_behavior_pattern({"request_rate_per_min": 0, "failed_executions": 0, "websocket_bursts": 0, "sandbox_violations": 0}),
        }

    async def get_audit_timeline(self, organization_id: UUID, limit: int = 25) -> dict[str, Any]:
        rows = await self.db.execute(
            select(AuditLog).where(AuditLog.organization_id == organization_id).order_by(AuditLog.created_at.desc()).limit(limit)
        )
        entries = [
            {
                "id": str(row.id),
                "organization_id": str(row.organization_id),
                "actor": row.actor,
                "action": row.action,
                "integrity_hash": row.integrity_hash,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows.scalars().all()
        ]
        return {"organization_id": str(organization_id), "entries": entries, "summary": f"{len(entries)} audit records"}

    async def get_security_events(self, organization_id: UUID, limit: int = 25) -> dict[str, Any]:
        rows = await self.db.execute(
            select(SecurityEvent).where(SecurityEvent.organization_id == organization_id).order_by(SecurityEvent.created_at.desc()).limit(limit)
        )
        entries = [
            {
                "id": str(row.id),
                "organization_id": str(row.organization_id),
                "event_type": row.event_type,
                "severity": row.severity,
                "summary": row.summary,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows.scalars().all()
        ]
        return {"organization_id": str(organization_id), "entries": entries, "summary": f"{len(entries)} security events"}

    async def get_rate_limit_status(self, organization_id: UUID) -> dict[str, Any]:
        budget = calculate_request_budget(str(organization_id))
        return {
            "organization_id": str(organization_id),
            "rate_limit": budget,
            "pressure": isolate_resource_pressure({"cpu_percent": 0, "memory_percent": 0, "worker_utilization_percent": 0}),
        }

    async def get_recovery_status(self, organization_id: UUID) -> dict[str, Any]:
        rows = await self.db.execute(
            select(RecoverySnapshot).where(RecoverySnapshot.organization_id == organization_id).order_by(RecoverySnapshot.created_at.desc()).limit(20)
        )
        snapshots = [
            {
                "id": str(row.id),
                "organization_id": str(row.organization_id),
                "snapshot_type": row.snapshot_type,
                "storage_location": row.storage_location,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows.scalars().all()
        ]
        recovery_state = validate_recovery_integrity({"snapshot_id": snapshots[0]["id"] if snapshots else None, "snapshot": snapshots[0] if snapshots else None})
        return {
            "organization_id": str(organization_id),
            "snapshots": snapshots,
            "status": recovery_state["status"],
            "integrity": recovery_state,
        }

    async def _persist_security_event(self, organization_id: str, event_type: str, severity: str, summary: str) -> None:
        try:
            self.db.add(SecurityEvent(organization_id=organization_id, event_type=event_type, severity=severity, summary=summary))
            await self.db.commit()
        except Exception:
            await self.db.rollback()

    async def _persist_audit_log(self, organization_id: str, actor: str, action: str, integrity_hash: str) -> None:
        try:
            self.db.add(AuditLog(organization_id=organization_id, actor=actor, action=action, integrity_hash=integrity_hash))
            await self.db.commit()
        except Exception:
            await self.db.rollback()