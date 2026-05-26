"""
IP reputation analysis helpers.
"""
from __future__ import annotations

from typing import Any
import ipaddress


MALICIOUS_HINTS = {"botnet", "scanner", "proxy", "tor", "malware", "abuse", "hosting"}


def calculate_reputation_score(signals: dict[str, Any]) -> float:
    """Calculate a normalized reputation score in the range 0.0-1.0."""
    score = 1.0
    score -= min(float(signals.get("abuse_reports") or 0) * 0.15, 0.6)
    score -= min(float(signals.get("malicious_hits") or 0) * 0.2, 0.5)
    score -= 0.25 if signals.get("is_public_cloud") else 0.0
    score -= 0.4 if signals.get("is_tor") else 0.0
    return round(min(max(score, 0.0), 1.0), 3)


def identify_malicious_hosts(hosts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag suspicious hosts using local signals and sanitized heuristics."""
    malicious_hosts: list[dict[str, Any]] = []
    for host in hosts:
        intel_text = " ".join(str(host.get(field, "")) for field in ("provider", "tag", "banner", "notes")).lower()
        malicious_hits = sum(1 for hint in MALICIOUS_HINTS if hint in intel_text)
        signals = {
            "abuse_reports": host.get("abuse_reports", 0),
            "malicious_hits": malicious_hits,
            "is_public_cloud": host.get("is_public_cloud", False),
            "is_tor": host.get("is_tor", False),
        }
        reputation = calculate_reputation_score(signals)
        if reputation < 0.55 or malicious_hits:
            malicious_hosts.append(
                {
                    "ip_address": host.get("ip_address"),
                    "hostname": host.get("hostname"),
                    "reputation_score": reputation,
                    "signals": signals,
                    "severity": "critical" if reputation < 0.25 else "high",
                }
            )
    return malicious_hosts


def analyze_ip_reputation(ip_address: str, observations: dict[str, Any] | None = None) -> dict[str, Any]:
    """Analyze a single IP address for suspicious infrastructure traits."""
    observations = observations or {}
    try:
        ip_obj = ipaddress.ip_address(ip_address)
    except ValueError:
        return {
            "ip_address": ip_address,
            "valid": False,
            "reputation_score": 0.0,
            "severity": "info",
            "summary": "Invalid IP address supplied.",
        }

    signals = {
        "abuse_reports": observations.get("abuse_reports", 0),
        "malicious_hits": observations.get("malicious_hits", 0),
        "is_public_cloud": observations.get("is_public_cloud", False),
        "is_tor": observations.get("is_tor", False),
    }
    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
        signals["malicious_hits"] = max(signals["malicious_hits"], 0)

    reputation_score = calculate_reputation_score(signals)
    severity = "critical" if reputation_score < 0.25 else "high" if reputation_score < 0.5 else "medium" if reputation_score < 0.75 else "low"

    return {
        "ip_address": ip_address,
        "valid": True,
        "reputation_score": reputation_score,
        "severity": severity,
        "signals": signals,
        "summary": "Suspicious infrastructure" if severity in {"critical", "high"} else "Low-risk infrastructure",
    }