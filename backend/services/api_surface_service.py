"""
API surface analysis service for endpoint discovery and risk scoring.
"""
from __future__ import annotations

from typing import Any


class APISurfaceService:
    """Discover and score API surfaces with GraphQL/OpenAPI awareness."""

    def identify_graphql(self, endpoints: list[str]) -> list[str]:
        """Identify likely GraphQL endpoints."""
        return sorted(
            set(
                ep for ep in endpoints
                if "graphql" in ep.lower() or ep.lower().endswith("/gql")
            )
        )

    def detect_api_surfaces(self, endpoints: list[str]) -> dict[str, Any]:
        """Detect API/OpenAPI/GraphQL surface indicators from endpoint list."""
        normalized = sorted(set(endpoints))

        api_endpoints = [ep for ep in normalized if "/api/" in ep.lower() or "/v1" in ep.lower() or "/v2" in ep.lower()]
        graphql_endpoints = self.identify_graphql(normalized)
        openapi_candidates = [
            ep for ep in normalized
            if any(x in ep.lower() for x in ["openapi", "swagger", "api-docs", "/docs"])
        ]

        return {
            "all_endpoints": normalized,
            "api_endpoints": api_endpoints,
            "graphql_endpoints": graphql_endpoints,
            "openapi_candidates": openapi_candidates,
            "parameter_rich_endpoints": [ep for ep in normalized if "?" in ep and ep.count("=") >= 1],
        }

    def analyze_api_risk(self, api_surface: dict[str, Any]) -> dict[str, Any]:
        """Compute high-signal API risk profile from discovered surfaces."""
        api_count = len(api_surface.get("api_endpoints", []))
        graphql_count = len(api_surface.get("graphql_endpoints", []))
        param_rich = len(api_surface.get("parameter_rich_endpoints", []))
        openapi_count = len(api_surface.get("openapi_candidates", []))

        score = 0
        score += min(api_count * 2, 30)
        score += min(graphql_count * 15, 30)
        score += min(param_rich * 4, 25)
        score += min(openapi_count * 5, 15)

        if score >= 70:
            level = "high"
        elif score >= 40:
            level = "medium"
        else:
            level = "low"

        hotspots = [
            *api_surface.get("graphql_endpoints", []),
            *api_surface.get("parameter_rich_endpoints", [])[:20],
        ]

        return {
            "api_risk_score": score,
            "risk_level": level,
            "hotspots": hotspots,
            "signals": {
                "api_count": api_count,
                "graphql_count": graphql_count,
                "parameter_rich_count": param_rich,
                "openapi_count": openapi_count,
            },
        }
