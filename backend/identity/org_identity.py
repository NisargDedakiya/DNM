"""
Organization identity mapping and federated role sync helpers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def map_user_to_org(user: dict[str, Any], organization_id: str, provider: str | None = None) -> dict[str, Any]:
    mapped = {
        "user_id": str(user.get("id") or user.get("user_id") or ""),
        "organization_id": organization_id,
        "username": user.get("username") or user.get("email") or "unknown",
        "email": user.get("email"),
        "provider": provider or user.get("provider") or "local",
        "role": user.get("role") or _default_role(provider),
        "mapped_at": datetime.now(timezone.utc).isoformat(),
    }
    return mapped


def resolve_org_identity(external_identity: str, provider: str, organization_id: str) -> dict[str, Any]:
    return {
        "external_identity": external_identity,
        "provider": provider,
        "organization_id": organization_id,
        "internal_subject": f"{organization_id}:{provider}:{external_identity}",
        "visibility": "org_scoped",
    }


def synchronize_org_roles(mapped_identity: dict[str, Any], federated_roles: list[str] | None = None) -> dict[str, Any]:
    roles = federated_roles or [mapped_identity.get("role") or "member"]
    normalized_roles = sorted({str(role).lower() for role in roles if role})
    return {
        "organization_id": mapped_identity.get("organization_id"),
        "user_id": mapped_identity.get("user_id"),
        "roles": normalized_roles,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }


def _default_role(provider: str | None) -> str:
    if provider in {"google_workspace", "microsoft_entra_id"}:
        return "enterprise_user"
    if provider == "okta":
        return "operator"
    if provider == "github_enterprise":
        return "security_researcher"
    return "member"
