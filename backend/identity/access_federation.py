"""
Federated access synchronization and validation helpers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def federate_access(identity_payload: dict[str, Any], provider: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "organization_id": identity_payload.get("organization_id"),
        "external_identity": identity_payload.get("external_identity") or identity_payload.get("email"),
        "federated_roles": [identity_payload.get("role") or "member"],
        "access_granted": True,
        "federated_at": datetime.now(timezone.utc).isoformat(),
    }


def synchronize_permissions(organization_id: str, user_id: str, permissions: list[str]) -> dict[str, Any]:
    deduped = sorted({str(permission).lower() for permission in permissions if permission})
    return {
        "organization_id": organization_id,
        "user_id": user_id,
        "permissions": deduped,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_federated_roles(federated_roles: list[str], allowed_roles: list[str] | None = None) -> dict[str, Any]:
    allowed = {str(role).lower() for role in (allowed_roles or ["enterprise_user", "operator", "security_researcher", "member", "admin"]) if role}
    normalized = [str(role).lower() for role in federated_roles if role]
    invalid = [role for role in normalized if role not in allowed]
    return {
        "valid": not invalid,
        "roles": normalized,
        "invalid_roles": invalid,
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }
