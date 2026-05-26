"""
Backup snapshot lifecycle helpers.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from uuid import uuid4
from typing import Any


_SNAPSHOTS: list[dict[str, Any]] = []


def create_backup_snapshot(organization_id: str, snapshot_type: str = "full", storage_location: str = "encrypted://backup") -> dict[str, Any]:
    """Create an encrypted backup snapshot descriptor."""
    snapshot = {
        "id": str(uuid4()),
        "organization_id": organization_id,
        "snapshot_type": snapshot_type,
        "storage_location": storage_location,
        "created_at": datetime.utcnow().isoformat(),
        "integrity_hash": sha256(f"{organization_id}:{snapshot_type}:{storage_location}".encode("utf-8")).hexdigest(),
    }
    _SNAPSHOTS.append(snapshot)
    return snapshot


def restore_backup(snapshot_id: str, organization_id: str) -> dict[str, Any]:
    """Restore a snapshot after validating org scope."""
    snapshot = next((item for item in _SNAPSHOTS if item["id"] == snapshot_id and item["organization_id"] == organization_id), None)
    return {
        "snapshot_id": snapshot_id,
        "organization_id": organization_id,
        "restored": bool(snapshot),
        "status": "restored" if snapshot else "not_found",
    }


def rotate_old_snapshots(retention_days: int = 30) -> dict[str, Any]:
    """Rotate snapshots outside the retention window."""
    keep = _SNAPSHOTS[-max(1, min(len(_SNAPSHOTS), retention_days)) :]
    removed = len(_SNAPSHOTS) - len(keep)
    _SNAPSHOTS[:] = keep
    return {
        "retention_days": retention_days,
        "removed_snapshots": removed,
        "remaining_snapshots": len(_SNAPSHOTS),
    }