"""
Technology fingerprint enrichment helpers.
"""
from __future__ import annotations

from typing import Any
import re


RISKY_TECHNOLOGIES = {
    "flash",
    "struts",
    "log4j",
    "weblogic",
    "jenkins",
    "grafana",
    "kibana",
    "graphql",
    "php",
    "apache",
}


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def detect_framework_versions(tech_stack: list[dict[str, Any]] | list[Any]) -> list[dict[str, Any]]:
    """Extract framework version intelligence from a technology stack."""
    results: list[dict[str, Any]] = []
    for technology in tech_stack:
        name = _normalize(getattr(technology, "name", None) or technology.get("name"))
        version = _normalize(getattr(technology, "version", None) or technology.get("version"))
        confidence = float(getattr(technology, "confidence_score", None) or technology.get("confidence_score") or technology.get("confidence") or 0.0)
        if not name:
            continue
        results.append(
            {
                "name": name,
                "version": version or None,
                "confidence": round(min(max(confidence, 0.0), 1.0), 3),
                "framework_like": any(token in name.lower() for token in ("react", "django", "flask", "spring", "express", "rails", "laravel", "next")),
            }
        )
    return results


def identify_risky_technologies(technologies: list[dict[str, Any]] | list[Any]) -> list[dict[str, Any]]:
    """Highlight technologies that deserve immediate threat correlation."""
    risky: list[dict[str, Any]] = []
    for technology in technologies:
        name = _normalize(getattr(technology, "name", None) or technology.get("name"))
        version = _normalize(getattr(technology, "version", None) or technology.get("version"))
        if not name:
            continue
        if any(keyword in name.lower() for keyword in RISKY_TECHNOLOGIES):
            severity = "critical" if any(token in version for token in ("0.", "1.", "2.")) else "high"
            risky.append(
                {
                    "name": name,
                    "version": version or None,
                    "severity": severity,
                    "reason": "Known high-signal or historically abused technology",
                }
            )
    return risky


def enrich_technology_stack(asset: dict[str, Any], technologies: list[dict[str, Any]] | list[Any]) -> dict[str, Any]:
    """Enrich an asset's technology stack with framework and risk context."""
    framework_versions = detect_framework_versions(technologies)
    risky = identify_risky_technologies(technologies)
    return {
        "asset": {
            "hostname": _normalize(asset.get("hostname")),
            "ip_address": _normalize(asset.get("ip_address")),
        },
        "framework_versions": framework_versions,
        "risky_technologies": risky,
        "summary": f"Detected {len(framework_versions)} technologies with {len(risky)} risky entries.",
    }