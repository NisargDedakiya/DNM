"""
Priority scoring and ranking for findings.

Provides modular, configurable scoring combining severity, exposure and evidence.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from backend.models.finding import Finding, SeverityLevel


DEFAULT_WEIGHTS = {
    "severity": 0.6,
    "exposure": 0.25,
    "evidence": 0.15,
}


def _severity_score(sev: Optional[SeverityLevel]) -> float:
    order = {"info": 0.1, "low": 0.3, "medium": 0.6, "high": 0.85, "critical": 1.0}
    if sev is None:
        return 0.0
    return float(order.get(sev.value if hasattr(sev, 'value') else str(sev), 0.0))


def _exposure_score(endpoint: Optional[str]) -> float:
    """Estimate exposure: public endpoints get higher score.

    Heuristic: endpoints that look like host paths (contains host and not localhost/private) -> 1.0
    If endpoint missing -> 0.2
    """
    if not endpoint:
        return 0.2
    # simple heuristic: presence of host/path indicates exposure
    if endpoint.startswith("http://") or endpoint.startswith("https://") or ":/" in endpoint:
        return 1.0
    return 0.6


def _evidence_score(evidence: Optional[str]) -> float:
    if not evidence:
        return 0.0
    ln = len(evidence)
    if ln < 50:
        return 0.2
    if ln < 200:
        return 0.6
    return 1.0


def calculate_priority_score(finding: Finding, weights: Dict[str, float] | None = None) -> float:
    w = weights or DEFAULT_WEIGHTS
    sev = _severity_score(finding.severity)
    exp = _exposure_score(finding.endpoint)
    ev = _evidence_score(finding.evidence)
    total = w["severity"] * sev + w["exposure"] * exp + w["evidence"] * ev
    denom = sum(w.values())
    if denom == 0:
        return 0.0
    return float(total / denom)


def rank_findings(findings: Iterable[Finding], weights: Dict[str, float] | None = None) -> List[Dict[str, object]]:
    """Return list of findings with priority score and risk level, sorted by score desc."""
    scored = []
    for f in findings:
        score = calculate_priority_score(f, weights)
        level = calculate_risk_level(score)
        scored.append({"finding_id": str(f.id), "score": score, "risk_level": level})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def calculate_risk_level(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    if score >= 0.2:
        return "low"
    return "info"
