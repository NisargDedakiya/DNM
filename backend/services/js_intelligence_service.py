"""
JavaScript intelligence service for endpoint extraction and sensitive pattern detection.
"""
from __future__ import annotations

import re
from typing import Any


_ENDPOINT_PATTERNS = [
    re.compile(r"['\"](/api/[a-zA-Z0-9_\-/{}:]+)['\"]"),
    re.compile(r"['\"](https?://[a-zA-Z0-9._~:/?#\[\]@!$&'()*+,;=%-]+)['\"]"),
    re.compile(r"fetch\(['\"]([^'\"]+)['\"]\)"),
    re.compile(r"axios\.(?:get|post|put|delete)\(['\"]([^'\"]+)['\"]\)"),
]

_SENSITIVE_PATTERNS = {
    "token_reference": re.compile(r"(?i)(token|jwt|bearer|authorization)"),
    "api_key_reference": re.compile(r"(?i)(api[_-]?key|client[_-]?secret)"),
    "debug_indicator": re.compile(r"(?i)(debug|devmode|__DEV__)"),
    "internal_endpoint_hint": re.compile(r"(?i)(internal|localhost|127\.0\.0\.1)"),
}


class JSIntelligenceService:
    """Analyze JavaScript artifacts for recon signal extraction."""

    def extract_endpoints(self, javascript_text: str) -> list[str]:
        """Extract route and URL indicators from JavaScript content."""
        text = javascript_text or ""
        found: list[str] = []

        for pattern in _ENDPOINT_PATTERNS:
            for match in pattern.findall(text):
                endpoint = match.strip()
                if endpoint and len(endpoint) <= 2048:
                    found.append(endpoint)

        return sorted(set(found))

    def detect_sensitive_patterns(self, javascript_text: str) -> list[dict[str, Any]]:
        """Detect risky sensitive references in JS source."""
        text = javascript_text or ""
        detections: list[dict[str, Any]] = []

        for name, pattern in _SENSITIVE_PATTERNS.items():
            for match in pattern.finditer(text):
                snippet_start = max(match.start() - 20, 0)
                snippet_end = min(match.end() + 40, len(text))
                snippet = text[snippet_start:snippet_end]
                detections.append({"pattern": name, "snippet": snippet})

        return detections

    def analyze_javascript(self, js_assets: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze JS assets and return endpoint/sensitive intelligence."""
        aggregate_endpoints: list[str] = []
        aggregate_patterns: list[dict[str, Any]] = []

        for asset in js_assets:
            body = str(asset.get("content") or "")
            endpoints = self.extract_endpoints(body)
            patterns = self.detect_sensitive_patterns(body)
            aggregate_endpoints.extend(endpoints)
            aggregate_patterns.extend(patterns)

        dedup_endpoints = sorted(set(aggregate_endpoints))

        return {
            "total_js_assets": len(js_assets),
            "extracted_endpoints": dedup_endpoints,
            "sensitive_pattern_hits": aggregate_patterns,
            "high_signal_endpoints": [
                ep for ep in dedup_endpoints
                if any(x in ep.lower() for x in ["/api", "graphql", "admin", "auth", "upload", "token"])
            ],
        }
