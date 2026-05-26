"""
Secret rotation and credential lifecycle helpers.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import sha256
from uuid import uuid4
from typing import Any


def validate_secret_integrity(secret_record: dict[str, Any]) -> dict[str, Any]:
    """Validate whether a secret record still appears consistent and active."""
    secret_value = str(secret_record.get("secret") or secret_record.get("value") or "")
    integrity_hash = sha256(secret_value.encode("utf-8")).hexdigest()
    expected = secret_record.get("integrity_hash")
    return {
        "secret_id": secret_record.get("secret_id") or secret_record.get("id"),
        "valid": bool(secret_value) and (expected is None or expected == integrity_hash),
        "integrity_hash": integrity_hash,
        "expires_at": secret_record.get("expires_at"),
    }


def rotate_secret(secret_record: dict[str, Any]) -> dict[str, Any]:
    """Generate a replacement secret without exposing the previous value."""
    rotated_value = f"rot_{uuid4().hex}"
    now = datetime.utcnow()
    return {
        "secret_id": secret_record.get("secret_id") or secret_record.get("id") or str(uuid4()),
        "organization_id": secret_record.get("organization_id"),
        "new_secret": rotated_value,
        "integrity_hash": sha256(rotated_value.encode("utf-8")).hexdigest(),
        "rotated_at": now.isoformat(),
        "expires_at": (now + timedelta(days=90)).isoformat(),
        "status": "rotated",
    }


def revoke_old_secret(secret_record: dict[str, Any]) -> dict[str, Any]:
    """Mark a legacy secret as revoked and invalidate it for future use."""
    return {
        "secret_id": secret_record.get("secret_id") or secret_record.get("id"),
        "organization_id": secret_record.get("organization_id"),
        "status": "revoked",
        "revoked_at": datetime.utcnow().isoformat(),
        "reason": secret_record.get("reason") or "rotation_complete",
    }