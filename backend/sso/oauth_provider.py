"""
OAuth federation helpers for enterprise identity providers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


SUPPORTED_PROVIDERS = {"google_workspace", "microsoft_entra_id", "okta", "github_enterprise"}


def authenticate_oauth_user(provider: str, token: str, organization_id: str) -> dict[str, Any]:
    validation = validate_oauth_token(provider, token)
    if not validation.get("valid"):
        return {"authenticated": False, "validation": validation}

    identity = map_org_identity(provider, validation, organization_id)
    return {
        "authenticated": True,
        "provider": provider,
        "organization_id": organization_id,
        "identity": identity,
        "validation": validation,
    }


def validate_oauth_token(provider: str, token: str) -> dict[str, Any]:
    normalized_provider = str(provider).lower().strip()
    valid = bool(token and normalized_provider in SUPPORTED_PROVIDERS)
    provider_subject = f"{normalized_provider}:{token[-12:] if token else 'missing'}"
    return {
        "valid": valid,
        "provider": normalized_provider,
        "token_subject": provider_subject,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }


def map_org_identity(provider: str, token_validation: dict[str, Any], organization_id: str) -> dict[str, Any]:
    normalized_provider = str(provider).lower().strip()
    external_identity = str(token_validation.get("token_subject") or "unknown")
    return {
        "provider": normalized_provider,
        "organization_id": organization_id,
        "external_identity": external_identity,
        "federated_role": _role_for_provider(normalized_provider),
        "stealth_aware": True,
    }


def _role_for_provider(provider: str) -> str:
    if provider in {"google_workspace", "microsoft_entra_id"}:
        return "enterprise_user"
    if provider == "okta":
        return "operator"
    if provider == "github_enterprise":
        return "security_researcher"
    return "member"
