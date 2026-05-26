"""
SAML federation helpers for enterprise authentication.
"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from typing import Any


def validate_saml_response(saml_response: str, organization_id: str, audience: str | None = None) -> dict[str, Any]:
    decoded = _safe_decode(saml_response)
    if not decoded:
        return {"valid": False, "reason": "empty_response", "organization_id": organization_id}

    digest = hashlib.sha256(decoded.encode("utf-8")).hexdigest()
    issuer = _extract_attribute(decoded, "Issuer")
    subject = _extract_attribute(decoded, "NameID")
    valid = bool(issuer and subject and organization_id)

    return {
        "valid": valid,
        "reason": None if valid else "invalid_assertion",
        "organization_id": organization_id,
        "issuer": issuer,
        "subject": subject,
        "audience": audience,
        "assertion_fingerprint": digest[:24],
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }


def authenticate_enterprise_user(saml_response: str, organization_id: str) -> dict[str, Any]:
    assertion = validate_saml_response(saml_response, organization_id)
    if not assertion.get("valid"):
        return {"authenticated": False, "assertion": assertion}

    identity = map_saml_identity(assertion)
    return {
        "authenticated": True,
        "organization_id": organization_id,
        "identity": identity,
        "assertion": assertion,
    }


def map_saml_identity(assertion: dict[str, Any]) -> dict[str, Any]:
    subject = str(assertion.get("subject") or "unknown")
    issuer = str(assertion.get("issuer") or "unknown")
    mapped_email = subject if "@" in subject else f"{subject}@{issuer.replace('https://', '').replace('/', '.')}.enterprise"
    return {
        "external_identity": subject,
        "provider": "saml",
        "organization_id": assertion.get("organization_id"),
        "mapped_email": mapped_email,
        "provider_issuer": issuer,
        "stealth_aware": True,
    }


def _safe_decode(saml_response: str) -> str:
    try:
        return base64.b64decode(saml_response).decode("utf-8")
    except Exception:
        return saml_response


def _extract_attribute(xml: str, attribute_name: str) -> str | None:
    token = f'{attribute_name}="'
    start = xml.find(token)
    if start == -1:
        return None
    start += len(token)
    end = xml.find('"', start)
    if end == -1:
        return None
    return xml[start:end]
