"""
Abuse detection for aggressive scans, suspicious execution, and abnormal patterns.
"""
from __future__ import annotations

from typing import Any


def analyze_behavior_pattern(activity: dict[str, Any]) -> dict[str, Any]:
    """Score activity for suspicious scanning or execution behavior."""
    request_rate = float(activity.get("request_rate_per_min") or 0)
    failures = float(activity.get("failed_executions") or 0)
    websocket_bursts = float(activity.get("websocket_bursts") or 0)
    sandbox_violations = float(activity.get("sandbox_violations") or 0)
    score = min(1.0, (request_rate / 100.0) * 0.35 + (failures / 10.0) * 0.2 + (websocket_bursts / 8.0) * 0.2 + (sandbox_violations / 5.0) * 0.25)
    return {
        "activity": activity,
        "abuse_score": round(score, 3),
        "severity": "critical" if score >= 0.8 else "high" if score >= 0.6 else "medium" if score >= 0.35 else "low",
    }


def detect_abuse_activity(activity: dict[str, Any]) -> dict[str, Any]:
    """Detect aggressive scanning or unusual execution patterns."""
    analysis = analyze_behavior_pattern(activity)
    suspicious = analysis["abuse_score"] >= 0.6 or bool(activity.get("scope_violation")) or bool(activity.get("approval_bypass_attempt"))
    return {
        **analysis,
        "suspicious": suspicious,
        "signals": [
            signal for signal, present in {
                "high_rate": float(activity.get("request_rate_per_min") or 0) > 120,
                "execution_failures": float(activity.get("failed_executions") or 0) > 3,
                "sandbox_violation": bool(activity.get("sandbox_violations")),
                "approval_bypass": bool(activity.get("approval_bypass_attempt")),
            }.items() if present
        ],
        "summary": "Abuse activity detected" if suspicious else "No abuse detected",
    }


def quarantine_suspicious_activity(activity: dict[str, Any]) -> dict[str, Any]:
    """Return a quarantined execution response without leaking sensitive details."""
    detection = detect_abuse_activity(activity)
    if detection["suspicious"]:
        return {
            **detection,
            "quarantined": True,
            "action": "isolate_execution",
            "recommended_controls": ["disable_tool_access", "require_manual_review", "pause_rate_budget"],
        }
    return {
        **detection,
        "quarantined": False,
        "action": "allow",
    }