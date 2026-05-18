"""
Confidence scoring service for false-positive reduction and signal weighting.
"""
from __future__ import annotations

from typing import Any


class ConfidenceService:
    """Deterministic confidence analysis for findings."""

    def detect_false_positive_patterns(self, context: dict[str, Any]) -> dict[str, Any]:
        """Identify patterns commonly correlated with false positives."""
        evidence = str(context.get("evidence") or "").lower()
        title = str(context.get("title") or "").lower()
        endpoint = str(context.get("endpoint") or "").lower()

        patterns: list[str] = []
        penalty = 0.0

        if "possible" in title or "potential" in title:
            patterns.append("weak_title_certainty")
            penalty += 0.08

        if "timeout" in evidence or "connection reset" in evidence:
            patterns.append("network_instability_signal")
            penalty += 0.12

        if "waf" in evidence or "blocked" in evidence:
            patterns.append("waf_interference")
            penalty += 0.10

        if endpoint and endpoint.count("/") <= 1 and "?" not in endpoint:
            patterns.append("low_context_endpoint")
            penalty += 0.05

        return {
            "patterns": patterns,
            "penalty": min(max(penalty, 0.0), 0.5),
            "likely_false_positive": penalty >= 0.25,
        }

    def score_finding_signal(self, context: dict[str, Any]) -> dict[str, Any]:
        """Score raw finding signal strength from contextual factors."""
        factors: dict[str, float] = {
            "technology_match": 0.0,
            "internet_exposure": 0.0,
            "auth_involvement": 0.0,
            "endpoint_sensitivity": 0.0,
            "exposure_context": 0.0,
            "duplication_level": 0.0,
        }

        fingerprints = [str(x).lower() for x in context.get("fingerprints", [])]
        endpoint = str(context.get("endpoint") or "").lower()
        exposure_count = int(context.get("related_exposure_count") or 0)
        duplicate_count = int(context.get("duplicate_count") or 0)
        internet_facing = bool(context.get("internet_facing", True))

        if fingerprints:
            factors["technology_match"] = 0.7
            if any(x in fingerprints for x in ["jenkins", "gitlab", "kubernetes", "wordpress", "graphql"]):
                factors["technology_match"] = 1.0

        factors["internet_exposure"] = 1.0 if internet_facing else 0.2

        if any(k in endpoint for k in ["auth", "login", "token", "oauth", "sso"]):
            factors["auth_involvement"] = 1.0
        elif any(k in endpoint for k in ["admin", "account", "session"]):
            factors["auth_involvement"] = 0.7

        if any(k in endpoint for k in ["admin", "upload", "graphql", "/api", "callback", "redirect", "internal"]):
            factors["endpoint_sensitivity"] = 1.0
        elif "?" in endpoint:
            factors["endpoint_sensitivity"] = 0.6

        factors["exposure_context"] = min(exposure_count / 4.0, 1.0)
        factors["duplication_level"] = 1.0 if duplicate_count == 0 else max(0.1, 1.0 - min(duplicate_count / 10.0, 0.9))

        weighted_score = (
            factors["technology_match"] * 0.20
            + factors["internet_exposure"] * 0.20
            + factors["auth_involvement"] * 0.20
            + factors["endpoint_sensitivity"] * 0.15
            + factors["exposure_context"] * 0.15
            + factors["duplication_level"] * 0.10
        )

        return {
            "factors": factors,
            "signal_score": min(max(weighted_score, 0.0), 1.0),
        }

    def calculate_confidence(self, context: dict[str, Any]) -> dict[str, Any]:
        """Compute final confidence score after false-positive adjustments."""
        signal = self.score_finding_signal(context)
        fp = self.detect_false_positive_patterns(context)

        base = float(signal["signal_score"])
        confidence = min(max(base - float(fp["penalty"]), 0.0), 1.0)

        label = "high" if confidence >= 0.8 else "medium" if confidence >= 0.55 else "low"

        return {
            "confidence_score": confidence,
            "confidence_label": label,
            "signal": signal,
            "false_positive": fp,
        }
