"""
AI triage service: analyzes findings and returns structured triage results.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from backend.ai import client, prompts
from backend.core.enums import FindingSeverity

logger = logging.getLogger(__name__)


class TriageResult:
    def __init__(self, severity: FindingSeverity, explanation: str, remediation: str, confidence: float):
        self.severity = severity
        self.explanation = explanation
        self.remediation = remediation
        self.confidence = confidence


async def triage_finding(title: str, severity: str | None, description: str, endpoint: str | None, evidence: str | None) -> TriageResult:
    prompt = prompts.render_triage_prompt(
        title=title,
        severity=severity or "",
        description=description or "",
        endpoint=endpoint or "",
        evidence=evidence or "",
    )

    try:
        resp = await client.analyze_finding(prompt)
    except Exception as exc:
        logger.exception("AI triage failed")
        # Fallback: mirror provided severity or default to 'low'
        fallback = FindingSeverity(low := "low")
        return TriageResult(fallback, "AI unavailable; fallback severity used.", "Manual review recommended.", 0.0)

    # Provider-specific parsing: try to extract text content
    text = None
    if isinstance(resp, dict):
        # attempt common keys
        text = resp.get("completion") or resp.get("text") or resp.get("output")
    if not text:
        text = str(resp)

    # Try parse JSON from text
    try:
        parsed = json.loads(text)
        rec = parsed.get("recommended_severity") or parsed.get("severity")
        explanation = parsed.get("explanation", "")
        remediation = parsed.get("remediation", "")
        confidence = float(parsed.get("confidence", 0.0))
    except Exception:
        # Best-effort extraction via simple heuristics
        rec = severity or "low"
        explanation = text[:1000]
        remediation = "Manual inspection required."
        confidence = 0.0

    # Normalize severity
    try:
        severity_enum = FindingSeverity(rec)
    except Exception:
        try:
            severity_enum = FindingSeverity(severity or "low")
        except Exception:
            severity_enum = FindingSeverity.low

    # sanitize strings
    explanation = (explanation or "").strip()
    remediation = (remediation or "").strip()

    return TriageResult(severity_enum, explanation, remediation, float(confidence))


async def explain_finding(*args: Any, **kwargs: Any) -> str:
    result = await triage_finding(*args, **kwargs)
    return result.explanation


async def suggest_remediation(*args: Any, **kwargs: Any) -> str:
    result = await triage_finding(*args, **kwargs)
    return result.remediation
