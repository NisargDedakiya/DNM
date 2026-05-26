"""
Auth mutation detector engine for NisargHunter AI continuous monitoring grid.
Detects changes in authentication endpoints, OAuth settings, and permission drift.
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.change_event import ChangeEvent

logger = logging.getLogger(__name__)


async def detect_auth_changes(asset_id: UUID, live_auth_endpoints: list[dict], db: AsyncSession) -> dict:
    """
    Compare current active authentication endpoints with historical baseline database state.

    Args:
        asset_id: UUID of the asset to analyze
        live_auth_endpoints: List of active auth endpoint configs
        db: Database session

    Returns:
        dict: Summary of auth surface additions, deletions, or scope changes.
    """
    logger.info("Detecting auth changes for asset: %s", asset_id)
    
    # Retrieve past change events to locate historical auth records
    stmt = select(ChangeEvent).where(
        ChangeEvent.asset_id == asset_id
    ).order_by(ChangeEvent.detected_at.desc()).limit(1)
    
    res = await db.execute(stmt)
    last_event = res.scalars().first()
    
    historical = []
    if last_event and last_event.new_value:
        historical = last_event.new_value.get("auth_endpoints", [])

    added = []
    removed = []
    modified = []

    # Simple matching based on URL path/method
    live_map = {f"{e.get('method')} {e.get('path')}": e for e in live_auth_endpoints}
    hist_map = {f"{e.get('method')} {e.get('path')}": e for e in historical}

    for key, live_val in live_map.items():
        if key not in hist_map:
            added.append(live_val)
        else:
            # Check if scope or config has mutated
            hist_val = hist_map[key]
            if live_val.get("scopes") != hist_val.get("scopes") or live_val.get("mfa_enabled") != hist_val.get("mfa_enabled"):
                modified.append({"path": key, "old": hist_val, "new": live_val})

    for key, hist_val in hist_map.items():
        if key not in live_map:
            removed.append(hist_val)

    return {
        "asset_id": str(asset_id),
        "checked_at": datetime.utcnow().isoformat(),
        "added_endpoints": added,
        "removed_endpoints": removed,
        "modified_endpoints": modified,
        "has_mutations": len(added) > 0 or len(removed) > 0 or len(modified) > 0,
    }


async def analyze_auth_exposure(url: str) -> dict:
    """
    Analyze login interface and SSO parameters to flag critical exposure risks.

    Args:
        url: URL of the auth page or endpoint (e.g. login portal, SSO redirect)

    Returns:
        dict: Detailed risk classification.
    """
    logger.info("Analyzing auth exposure for url: %s", url)
    
    findings = []
    risk_score = 0.0

    # Pattern check: HTTP vs HTTPS
    if url.startswith("http://"):
        risk_score += 5.0
        findings.append({
            "vulnerability": "Cleartext Authentication Route",
            "impact": "Credentials sent over unencrypted HTTP protocol.",
            "severity": "high",
        })

    # Pattern check: OAuth redirect parameters
    if "redirect_uri=" in url:
        # Check if redirect is wildcard or relative (potential open redirect)
        if "redirect_uri=*" in url or "redirect_uri=http%3A%2F%2Flocalhost" in url:
            risk_score += 4.5
            findings.append({
                "vulnerability": "Permissive OAuth Callback Redirect URI",
                "impact": "Allows attackers to hijack authorization codes.",
                "severity": "high",
            })

    # Pattern check: SSO/SSRF paths
    if "sso" in url or "saml" in url:
        # SSO configuration endpoints should check for XML signatures / state parameter
        if "state=" not in url and "oauth" in url:
            risk_score += 3.0
            findings.append({
                "vulnerability": "Missing CSRF State Protection",
                "impact": "Login CSRF vulnerability in OAuth workflow.",
                "severity": "medium",
            })

    risk_score = min(risk_score, 10.0)
    risk_level = "info"
    if risk_score >= 8.0:
        risk_level = "critical"
    elif risk_score >= 5.0:
        risk_level = "high"
    elif risk_score >= 3.0:
        risk_level = "medium"
    elif risk_score > 0.0:
        risk_level = "low"

    return {
        "url": url,
        "findings": findings,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "analyzed_at": datetime.utcnow().isoformat(),
    }


async def identify_permission_drift(live_roles: dict, historical_roles: dict) -> dict:
    """
    Identify permission changes or SSO role drift to detect privilege escalations.

    Args:
        live_roles: Current active permissions mapping (e.g. {"admin": ["*"], "user": ["read"]})
        historical_roles: Baseline permissions mapping

    Returns:
        dict: Drift details and authorization risk indicator.
    """
    logger.info("Checking permission drift across SSO roles")
    drifts = []
    has_drift = False

    for role, permissions in live_roles.items():
        hist_perms = historical_roles.get(role, [])
        elevated = list(set(permissions) - set(hist_perms))
        revoked = list(set(hist_perms) - set(permissions))

        if elevated:
            has_drift = True
            drifts.append({
                "role": role,
                "action": "privilege_elevation",
                "added_permissions": elevated,
                "description": f"Role '{role}' gained new permissions: {elevated}",
            })
        if revoked:
            has_drift = True
            drifts.append({
                "role": role,
                "action": "permission_reduction",
                "removed_permissions": revoked,
                "description": f"Role '{role}' lost permissions: {revoked}",
            })

    return {
        "checked_at": datetime.utcnow().isoformat(),
        "has_permission_drift": has_drift,
        "drifts": drifts,
        "risk_status": "high" if any(d["action"] == "privilege_elevation" for d in drifts) else "low",
    }
