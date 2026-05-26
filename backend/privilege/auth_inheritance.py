"""
Authentication trust inheritance helpers.
"""
from __future__ import annotations

from typing import Any


def analyze_auth_inheritance(auth_context: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze OAuth/JWT delegation and trust inheritance."""
    trust_tokens = correlate_trust_tokens(auth_context)
    propagations = identify_auth_propagation(auth_context)
    risk = round(min(10.0, len(trust_tokens) * 1.5 + len(propagations) * 1.2), 2)
    return {
        "trust_tokens": trust_tokens,
        "propagations": propagations,
        "auth_inheritance_risk": risk,
        "severity": "critical" if risk >= 8.5 else "high" if risk >= 6.0 else "medium",
        "summary": f"Evaluated {len(auth_context)} auth trust relationships.",
    }


def correlate_trust_tokens(auth_context: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Correlate OAuth/JWT trust tokens and delegation paths."""
    tokens = []
    for item in auth_context:
        token_type = str(item.get("token_type") or item.get("auth_type") or "jwt").lower()
        if token_type in {"jwt", "oauth", "oauth2", "saml"}:
            tokens.append(
                {
                    "source": item.get("source"),
                    "target": item.get("target"),
                    "token_type": token_type,
                    "delegation": bool(item.get("delegation") or item.get("inheritance")),
                }
            )
    return tokens


def identify_auth_propagation(auth_context: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Identify auth propagation opportunities across trust boundaries."""
    propagations = []
    for item in auth_context:
        if item.get("delegation") or item.get("inheritance") or float(item.get("trust_score") or 0.0) >= 0.6:
            propagations.append(
                {
                    "source": item.get("source"),
                    "target": item.get("target"),
                    "auth_flow": item.get("auth_flow") or "delegated_session",
                    "severity": item.get("severity") or "high",
                }
            )
    return propagations