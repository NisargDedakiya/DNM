"""
Remediation service for contextual, defensive vulnerability fix guidance.
"""
from __future__ import annotations

from typing import Any

from backend.ai.report_writer import generate_remediation


class RemediationService:
    """Builds remediation guidance with clear verification steps and best practices."""

    def explain_security_fix(
        self,
        vulnerability_type: str,
        technology_stack: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Explain defensive fix strategy in implementation-ready language."""
        vuln = str(vulnerability_type or "security issue").strip().lower()
        stack = str(technology_stack or "application stack").strip()

        if "auth" in vuln or "bypass" in vuln:
            return (
                f"In {stack}, enforce server-side authorization on every privileged endpoint, "
                "validate session/token integrity, and deny-by-default for sensitive actions."
            )
        if "ssrf" in vuln:
            return (
                f"In {stack}, apply strict outbound destination allowlists, block internal metadata ranges, "
                "and normalize URL parsing before request dispatch."
            )
        if "graphql" in vuln:
            return (
                f"In {stack}, disable introspection in production when possible, enforce query depth/complexity limits, "
                "and apply resolver-level authorization checks."
            )
        if "upload" in vuln:
            return (
                f"In {stack}, enforce MIME and extension validation, isolate upload storage, and perform malware/content scanning "
                "before serving files."
            )
        if "api" in vuln:
            return (
                f"In {stack}, enforce schema validation, object-level authorization, and robust rate limits with anomaly monitoring."
            )

        return (
            f"In {stack}, tighten access control, validate user-controlled input, and add regression coverage for the vulnerable flow."
        )

    def suggest_best_practices(self, vulnerability_type: str, asset_type: str | None = None) -> list[str]:
        """Suggest practical secure engineering controls by vulnerability and asset context."""
        vuln = str(vulnerability_type or "").lower()
        asset = str(asset_type or "application").lower()

        controls = [
            "Enforce least privilege and explicit authorization checks on sensitive operations.",
            "Add structured security logging for denied access and abnormal request patterns.",
            "Include regression security tests in CI for the affected workflow.",
        ]

        if "cloud" in vuln or "cloud" in asset:
            controls.append("Restrict IAM permissions and block public exposure of internal cloud resources.")
        if "api" in vuln or "api" in asset:
            controls.append("Apply schema-based input validation and object-level authorization across API handlers.")
        if "graphql" in vuln:
            controls.append("Enforce query complexity limits and resolver-level authorization rules.")
        if "auth" in vuln:
            controls.append("Harden session management with short-lived tokens and strict token validation.")

        return controls

    async def generate_remediation_guidance(
        self,
        context: dict[str, Any],
        organization_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate remediation package with AI advisory and deterministic best-practice overlays."""
        vulnerability_type = str(context.get("vulnerability_type") or context.get("title") or "security issue")
        technology_stack = str(context.get("technology_stack") or "application stack")
        asset_type = str(context.get("asset_type") or context.get("affected_asset") or "application")

        ai_guidance = await generate_remediation(context, organization_id=organization_id)
        fix_explanation = self.explain_security_fix(vulnerability_type, technology_stack, context)
        best_practices = self.suggest_best_practices(vulnerability_type, asset_type)

        return {
            "remediation_summary": ai_guidance.get("remediation_summary") or fix_explanation,
            "fix_steps": ai_guidance.get("fix_steps", []),
            "verification_plan": ai_guidance.get("verification_plan", []),
            "security_fix_explanation": fix_explanation,
            "best_practices": best_practices,
            "human_review_required": True,
            "advisory_only": True,
        }
