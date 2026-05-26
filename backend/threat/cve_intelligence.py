"""
CVE intelligence helpers for version-to-vulnerability correlation.

All functions are deterministic, async-safe, and work on sanitized local data.
They do not fetch external feeds directly; callers can hydrate them with data
from approved intelligence sources.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re


_SEVERITY_ORDER = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}


@dataclass(slots=True)
class CVERecord:
    cve_id: str
    title: str
    severity: str
    cvss_score: float
    affected_versions: list[str]
    exploitability: float = 0.0
    references: list[str] | None = None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _version_matches(version: str | None, affected_versions: list[str]) -> bool:
    if not version:
        return False
    normalized = version.lower()
    return any(token.lower() in normalized for token in affected_versions if token)


def _score_exploitability(record: CVERecord) -> float:
    severity_boost = _SEVERITY_ORDER.get(record.severity.lower(), 0) / 4.0
    score = (record.cvss_score / 10.0) * 0.7 + severity_boost * 0.3
    if record.exploitability > 0:
        score = max(score, min(record.exploitability, 1.0))
    return round(min(max(score, 0.0), 1.0), 3)


def map_cves(
    technologies: list[dict[str, Any]] | list[Any],
    cve_catalog: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Correlate software versions to CVE records.

    Args:
        technologies: technology payloads containing name/version metadata.
        cve_catalog: optional curated CVE feed.

    Returns:
        Sanitized CVE matches ordered by severity and exploitability.
    """
    catalog = [
        CVERecord(
            cve_id=_normalize_text(item.get("cve_id")),
            title=_normalize_text(item.get("title") or item.get("summary")),
            severity=_normalize_text(item.get("severity") or "medium").lower(),
            cvss_score=float(item.get("cvss_score") or item.get("score") or 0.0),
            affected_versions=[_normalize_text(token) for token in item.get("affected_versions", [])],
            exploitability=float(item.get("exploitability") or 0.0),
            references=[_normalize_text(ref) for ref in item.get("references", [])] if item.get("references") else None,
        )
        for item in (cve_catalog or [])
        if item.get("cve_id")
    ]

    matches: list[dict[str, Any]] = []
    for technology in technologies:
        tech_name = _normalize_text(getattr(technology, "name", None) or technology.get("name"))
        version = _normalize_text(getattr(technology, "version", None) or technology.get("version"))
        if not tech_name:
            continue

        for record in catalog:
            if tech_name.lower() not in record.title.lower() and not _version_matches(version, record.affected_versions):
                continue

            exploitability = _score_exploitability(record)
            matches.append(
                {
                    "technology": tech_name,
                    "version": version or None,
                    "cve_id": record.cve_id,
                    "title": record.title,
                    "severity": record.severity,
                    "cvss_score": round(record.cvss_score, 1),
                    "exploitability": exploitability,
                    "references": record.references or [],
                }
            )

    return prioritize_exploitable_cves(matches)


def analyze_cve_risk(cve_match: dict[str, Any]) -> dict[str, Any]:
    """Calculate severity-aware risk summary for a mapped CVE."""
    severity = _normalize_text(cve_match.get("severity") or "medium").lower()
    severity_score = _SEVERITY_ORDER.get(severity, 1)
    cvss_score = float(cve_match.get("cvss_score") or 0.0)
    exploitability = float(cve_match.get("exploitability") or 0.0)

    risk_score = round(
        min(10.0, (cvss_score * 0.6) + (severity_score * 1.2) + (exploitability * 2.0)),
        2,
    )
    priority = "critical" if risk_score >= 8.5 else "high" if risk_score >= 6.5 else "medium" if risk_score >= 4.0 else "low"

    return {
        **cve_match,
        "risk_score": risk_score,
        "priority": priority,
        "exploit_window": "active" if exploitability >= 0.75 else "monitor",
    }


def prioritize_exploitable_cves(cves: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort CVEs by exploitability, severity, and CVSS."""
    enriched = [analyze_cve_risk(cve) for cve in cves]
    return sorted(
        enriched,
        key=lambda item: (
            item.get("risk_score", 0.0),
            item.get("exploitability", 0.0),
            item.get("cvss_score", 0.0),
        ),
        reverse=True,
    )