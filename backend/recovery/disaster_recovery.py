"""
Disaster recovery orchestration helpers.
"""
from __future__ import annotations

from typing import Any

from backend.recovery.backup_manager import create_backup_snapshot, restore_backup, rotate_old_snapshots


def initiate_recovery(organization_id: str, incident: dict[str, Any]) -> dict[str, Any]:
    """Kick off an org-scoped recovery workflow."""
    snapshot = create_backup_snapshot(organization_id, snapshot_type=incident.get("snapshot_type", "full"))
    return {
        "organization_id": organization_id,
        "incident": incident,
        "snapshot": snapshot,
        "recovery_stage": "initiated",
        "status": "in_progress",
    }


def restore_cluster_state(organization_id: str, snapshot_id: str) -> dict[str, Any]:
    """Restore cluster state from a backup snapshot."""
    restored = restore_backup(snapshot_id, organization_id)
    return {
        "organization_id": organization_id,
        "snapshot_id": snapshot_id,
        "restoration": restored,
        "status": restored["status"],
    }


def validate_recovery_integrity(recovery_state: dict[str, Any]) -> dict[str, Any]:
    """Validate that the recovery workflow is internally consistent."""
    has_snapshot = bool(recovery_state.get("snapshot") or recovery_state.get("snapshot_id"))
    status = "valid" if has_snapshot else "invalid"
    return {
        "valid": has_snapshot,
        "status": status,
        "summary": "Recovery state validated" if has_snapshot else "Recovery state incomplete",
    }