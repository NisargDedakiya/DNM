"""
External intelligence correlation and risk prioritization helpers.
"""
from __future__ import annotations

from typing import Any


def calculate_exploitability_score(signals: dict[str, Any]) -> float:
    """Calculate a normalized exploitability score from multiple signals."""
    score = 0.0
    score += float(signals.get("cve_severity_score") or 0.0) * 0.35
    score += float(signals.get("public_exposure_score") or 0.0) * 0.2
    score += float(signals.get("credential_exposure_score") or 0.0) * 0.25
    score += float(signals.get("reputation_penalty") or 0.0) * 0.2
    return round(min(max(score, 0.0), 10.0), 2)


def correlate_threat_signals(exposure_context: dict[str, Any]) -> dict[str, Any]:
    """Combine threat signals into a sanitized correlation payload."""
    signals = {
        "cves": exposure_context.get("cves", []),
        "public_services": exposure_context.get("public_services", []),
        "secret_leaks": exposure_context.get("secret_leaks", []),
        "ip_reputation": exposure_context.get("ip_reputation", {}),
        "asn": exposure_context.get("asn", {}),
    }

    cve_severity_score = max((float(item.get("risk_score") or 0.0) for item in signals["cves"]), default=0.0)
    public_exposure_score = min(len([item for item in signals["public_services"] if item.get("is_public")]) * 1.5, 5.0)
    credential_exposure_score = min(len(signals["secret_leaks"]) * 2.0, 5.0)
    reputation_penalty = 0.0
    ip_summary = signals["ip_reputation"]
    if ip_summary:
        reputation_penalty = max(0.0, 1.0 - float(ip_summary.get("reputation_score") or 0.0)) * 5.0

    exploitability = calculate_exploitability_score(
        {
            "cve_severity_score": cve_severity_score,
            "public_exposure_score": public_exposure_score,
            "credential_exposure_score": credential_exposure_score,
            "reputation_penalty": reputation_penalty,
        }
    )

    severity = "critical" if exploitability >= 8.0 else "high" if exploitability >= 6.0 else "medium" if exploitability >= 3.5 else "low"
    return {
        "signals": signals,
        "exploitability_score": exploitability,
        "severity": severity,
        "summary": "Correlated external intelligence across CVE, exposure, credential, and reputation signals.",
    }


def prioritize_external_risk(correlated_signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank correlated findings by severity and exploitability."""
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    return sorted(
        correlated_signals,
        key=lambda item: (
            severity_rank.get(str(item.get("severity") or "low"), 0),
            float(item.get("exploitability_score") or 0.0),
        ),
        reverse=True,
    )