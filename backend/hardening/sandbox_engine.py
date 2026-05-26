"""
Sandbox execution helpers for isolated offensive and AI-assisted operations.
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any


DEFAULT_QUOTAS = {
    "cpu_percent": 35,
    "memory_mb": 512,
    "disk_mb": 256,
    "network_egress_mb": 25,
}


def create_execution_sandbox(organization_id: str, actor: str, tool_name: str, timeout_seconds: int = 300, quotas: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a sanitized sandbox descriptor for a scoped execution."""
    sandbox_quotas = dict(DEFAULT_QUOTAS)
    if quotas:
        sandbox_quotas.update({key: value for key, value in quotas.items() if key in sandbox_quotas})

    return {
        "sandbox_id": str(uuid4()),
        "organization_id": organization_id,
        "actor": actor,
        "tool_name": tool_name,
        "timeout_seconds": max(30, min(timeout_seconds, 1800)),
        "quotas": sandbox_quotas,
        "created_at": datetime.utcnow().isoformat(),
        "status": "created",
    }


def enforce_resource_limits(sandbox: dict[str, Any], resource_usage: dict[str, Any] | None = None) -> dict[str, Any]:
    """Clamp resource usage to sandbox quotas and report violations."""
    resource_usage = resource_usage or {}
    quotas = sandbox.get("quotas", DEFAULT_QUOTAS)
    violations: list[str] = []
    usage_snapshot: dict[str, Any] = {}

    for key, limit in quotas.items():
        value = float(resource_usage.get(key, 0) or 0)
        usage_snapshot[key] = value
        if value > float(limit):
            violations.append(key)

    sandbox["resource_usage"] = usage_snapshot
    sandbox["violations"] = violations
    sandbox["status"] = "bounded" if not violations else "throttled"
    return sandbox


def cleanup_sandbox(sandbox: dict[str, Any]) -> dict[str, Any]:
    """Mark the sandbox as cleaned and strip transient execution state."""
    cleaned = dict(sandbox)
    cleaned.pop("resource_usage", None)
    cleaned.pop("violations", None)
    cleaned["status"] = "destroyed"
    cleaned["cleaned_at"] = datetime.utcnow().isoformat()
    return cleaned