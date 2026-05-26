"""
Secure enterprise session manager with org and stealth awareness.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4


_SESSIONS: dict[str, dict[str, Any]] = {}


def create_enterprise_session(
    user_id: str,
    organization_id: str,
    provider: str,
    stealth_workspace_id: str | None = None,
    expires_in_minutes: int = 480,
) -> dict[str, Any]:
    session_id = str(uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=max(5, int(expires_in_minutes)))
    session = {
        "session_id": session_id,
        "user_id": user_id,
        "organization_id": organization_id,
        "provider": provider,
        "stealth_workspace_id": stealth_workspace_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at.isoformat(),
        "active": True,
    }
    _SESSIONS[session_id] = session
    return session


def validate_session(session_id: str, organization_id: str | None = None) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if not session:
        return {"valid": False, "reason": "missing_session"}

    expires_at = datetime.fromisoformat(session["expires_at"])
    if expires_at <= datetime.now(timezone.utc):
        return {"valid": False, "reason": "expired_session", "session_id": session_id}

    if organization_id and str(session.get("organization_id")) != str(organization_id):
        return {"valid": False, "reason": "org_mismatch", "session_id": session_id}

    return {"valid": True, **session}


def terminate_session(session_id: str) -> dict[str, Any]:
    session = _SESSIONS.pop(session_id, None)
    return {
        "terminated": bool(session),
        "session_id": session_id,
        "organization_id": session.get("organization_id") if session else None,
    }
