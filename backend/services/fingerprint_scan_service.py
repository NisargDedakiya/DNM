"""
Fingerprint-aware scan strategy service.
"""
from __future__ import annotations

from typing import Any


RISKY_TECH = {
    "wordpress": 80,
    "jenkins": 95,
    "gitlab": 90,
    "grafana": 85,
    "kubernetes": 95,
    "phpmyadmin": 90,
    "elasticsearch": 88,
    "graphql": 82,
}

TECH_TEMPLATE_MAP = {
    "wordpress": ["wordpress", "cves", "misconfiguration"],
    "jenkins": ["jenkins", "cves", "exposures"],
    "gitlab": ["gitlab", "cves", "misconfiguration"],
    "grafana": ["grafana", "misconfiguration"],
    "kubernetes": ["kubernetes", "exposures"],
    "graphql": ["graphql", "misconfiguration"],
    "default": ["misconfiguration", "exposures", "cves"],
}

HIGH_VALUE_HINTS = [
    "admin",
    "auth",
    "api",
    "graphql",
    "upload",
    "dashboard",
    "staging",
    "dev",
]


class FingerprintScanService:
    """Generate targeted high-signal scan plans from fingerprint intelligence."""

    def match_fingerprint_templates(self, fingerprints: list[str]) -> list[str]:
        """Map fingerprints to relevant template tags."""
        tags: list[str] = []
        for fp in fingerprints:
            tags.extend(TECH_TEMPLATE_MAP.get(fp.lower(), []))

        if not tags:
            tags = TECH_TEMPLATE_MAP["default"].copy()

        return sorted(set(tags))

    def prioritize_high_risk_assets(self, assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank assets by high-value hints and risky technology signals."""
        scored: list[tuple[int, dict[str, Any]]] = []

        for asset in assets:
            host = str(asset.get("target") or asset.get("hostname") or "").lower()
            fingerprints = [str(x).lower() for x in asset.get("fingerprints", [])]

            score = 0
            for hint in HIGH_VALUE_HINTS:
                if hint in host:
                    score += 12

            for fp in fingerprints:
                score += RISKY_TECH.get(fp, 20)

            if asset.get("internet_facing", True):
                score += 15

            scored.append((score, {**asset, "priority_score": score}))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [asset for _, asset in scored]

    def generate_scan_strategy(self, assets: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate stage-specific scan strategy for prioritized assets."""
        prioritized_assets = self.prioritize_high_risk_assets(assets)

        strategy_targets: list[dict[str, Any]] = []
        for asset in prioritized_assets:
            fingerprints = asset.get("fingerprints", [])
            template_tags = self.match_fingerprint_templates(fingerprints)

            strategy_targets.append(
                {
                    "target": asset.get("target") or asset.get("hostname"),
                    "priority_score": asset.get("priority_score", 0),
                    "fingerprints": fingerprints,
                    "nuclei_tags": template_tags,
                    "run_dalfox": any(k in str(asset.get("target", "")).lower() for k in ["auth", "login", "search", "api"]),
                    "run_ffuf": any(k in str(asset.get("target", "")).lower() for k in ["admin", "api", "upload", "dashboard"]),
                    "sqlmap_candidate": any(k in str(asset.get("target", "")).lower() for k in ["id=", "item=", "query=", "product="]),
                }
            )

        return {
            "total_assets": len(assets),
            "prioritized_targets": strategy_targets,
            "high_value_targets": [t for t in strategy_targets if t["priority_score"] >= 80],
        }
