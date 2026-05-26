"""
Immutable audit trail helpers.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Any


def _hash_payload(payload: dict[str, Any], previous_hash: str | None = None) -> str:
    base = repr(sorted(payload.items())) + (previous_hash or "")
    return sha256(base.encode("utf-8")).hexdigest()


def generate_audit_entry(organization_id: str, actor: str, action: str, payload: dict[str, Any] | None = None, previous_hash: str | None = None) -> dict[str, Any]:
    """Create an immutable audit entry with hash chaining."""
    payload = payload or {}
    integrity_hash = _hash_payload({"organization_id": organization_id, "actor": actor, "action": action, **payload}, previous_hash=previous_hash)
    return {
        "organization_id": organization_id,
        "actor": actor,
        "action": action,
        "payload": payload,
        "integrity_hash": integrity_hash,
        "previous_hash": previous_hash,
        "created_at": datetime.utcnow().isoformat(),
    }


def verify_log_integrity(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify the hash chain of an audit log sequence."""
    previous_hash = None
    tampered = []
    for index, entry in enumerate(entries):
        expected = _hash_payload(
            {
                "organization_id": entry.get("organization_id"),
                "actor": entry.get("actor"),
                "action": entry.get("action"),
                **(entry.get("payload") or {}),
            },
            previous_hash=previous_hash,
        )
        if entry.get("integrity_hash") != expected:
            tampered.append(index)
        previous_hash = entry.get("integrity_hash")
    return {
        "valid": not tampered,
        "tampered_indexes": tampered,
        "record_count": len(entries),
    }


def detect_audit_tampering(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a concise tamper-detection summary."""
    integrity = verify_log_integrity(entries)
    return {
        **integrity,
        "severity": "critical" if not integrity["valid"] else "info",
        "summary": "Audit chain tampering detected" if not integrity["valid"] else "Audit chain intact",
    }