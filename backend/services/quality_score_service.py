"""
Quality scoring service for AI-assisted vulnerability report drafts.
"""
from __future__ import annotations

from typing import Any


class QualityScoreService:
    """Scores report quality on clarity, reproducibility, impact clarity, and technical depth."""

    def _normalize_text(self, value: Any) -> str:
        return str(value or "").strip()

    def _evaluate_clarity(self, report_data: dict[str, Any]) -> float:
        title = self._normalize_text(report_data.get("title"))
        summary = self._normalize_text(report_data.get("summary"))
        details = self._normalize_text(report_data.get("technical_details"))

        score = 0.0
        if 8 <= len(title) <= 255:
            score += 35.0
        if len(summary) >= 80:
            score += 35.0
        if len(details) >= 120:
            score += 30.0
        return min(score, 100.0)

    def evaluate_reproducibility(self, report_data: dict[str, Any]) -> float:
        """Score reproduction quality from prerequisites, steps, and checks."""
        steps = [str(step).strip() for step in report_data.get("steps_to_reproduce", []) if str(step).strip()]
        affected_asset = self._normalize_text(report_data.get("affected_asset"))
        evidence = self._normalize_text(report_data.get("evidence"))

        score = 0.0
        if len(steps) >= 3:
            score += 45.0
        elif len(steps) == 2:
            score += 30.0
        elif len(steps) == 1:
            score += 15.0

        if affected_asset:
            score += 25.0
        if len(evidence) >= 60:
            score += 30.0

        return min(score, 100.0)

    def evaluate_impact_clarity(self, report_data: dict[str, Any]) -> float:
        """Score impact explanation quality and practical business linkage."""
        impact = self._normalize_text(report_data.get("business_impact"))
        workflows = [str(item).strip() for item in report_data.get("impact_workflows", []) if str(item).strip()]
        severity = self._normalize_text(report_data.get("severity"))

        score = 0.0
        if len(impact) >= 80:
            score += 50.0
        if len(workflows) >= 1:
            score += 30.0
        if severity:
            score += 20.0

        return min(score, 100.0)

    def evaluate_technical_depth(self, report_data: dict[str, Any]) -> float:
        """Score technical precision and remediation completeness."""
        details = self._normalize_text(report_data.get("technical_details"))
        remediation_steps = [
            str(item).strip() for item in report_data.get("remediation_steps", []) if str(item).strip()
        ]
        references = [str(item).strip() for item in report_data.get("references", []) if str(item).strip()]

        score = 0.0
        if len(details) >= 200:
            score += 45.0
        elif len(details) >= 120:
            score += 30.0
        if len(remediation_steps) >= 2:
            score += 35.0
        elif len(remediation_steps) == 1:
            score += 20.0
        if len(references) >= 1:
            score += 20.0

        return min(score, 100.0)

    def calculate_quality_score(self, report_data: dict[str, Any]) -> dict[str, Any]:
        """Calculate weighted final quality score (0-100) and identify weak dimensions."""
        clarity = self._evaluate_clarity(report_data)
        reproducibility = self.evaluate_reproducibility(report_data)
        impact_clarity = self.evaluate_impact_clarity(report_data)
        technical_depth = self.evaluate_technical_depth(report_data)

        final_score = (
            (clarity * 0.25)
            + (reproducibility * 0.30)
            + (impact_clarity * 0.25)
            + (technical_depth * 0.20)
        )

        weak_dimensions: list[str] = []
        if clarity < 60:
            weak_dimensions.append("clarity")
        if reproducibility < 60:
            weak_dimensions.append("reproducibility")
        if impact_clarity < 60:
            weak_dimensions.append("business_impact")
        if technical_depth < 60:
            weak_dimensions.append("technical_depth")

        return {
            "final_score": round(max(0.0, min(final_score, 100.0)), 2),
            "breakdown": {
                "clarity": round(clarity, 2),
                "reproducibility": round(reproducibility, 2),
                "impact_clarity": round(impact_clarity, 2),
                "technical_depth": round(technical_depth, 2),
            },
            "weak_dimensions": weak_dimensions,
            "human_review_required": True,
        }
