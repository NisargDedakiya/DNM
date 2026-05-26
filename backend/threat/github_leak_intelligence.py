"""
GitHub leak intelligence helpers for secret and token exposure analysis.

These helpers only emit sanitized findings. Raw secrets are never returned.
"""
from __future__ import annotations

from typing import Any
import re


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{8,})"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


def _mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


def detect_secret_leaks(repositories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Identify repositories with likely leaked secrets."""
    leaks: list[dict[str, Any]] = []
    for repository in repositories:
        text = str(repository.get("content", ""))
        matches = []
        for pattern in SECRET_PATTERNS:
            for match in pattern.findall(text):
                secret = match[1] if isinstance(match, tuple) else match
                matches.append(_mask_secret(secret))

        if matches:
            leaks.append(
                {
                    "repository": repository.get("repository") or repository.get("name"),
                    "owner": repository.get("owner"),
                    "detected_secrets": sorted(set(matches)),
                    "severity": "critical" if len(matches) >= 2 else "high",
                }
            )

    return leaks


def analyze_repository_exposure(repository: dict[str, Any]) -> dict[str, Any]:
    """Summarize how exposed a repository appears to be."""
    visibility = str(repository.get("visibility") or "private").lower()
    archived = bool(repository.get("archived"))
    collaborators = int(repository.get("collaborators") or 0)
    token_indicators = detect_secret_leaks([repository])

    severity = "low"
    if visibility == "public":
        severity = "medium"
    if token_indicators:
        severity = "critical"
    if archived and visibility == "public":
        severity = "high"

    return {
        "repository": repository.get("repository") or repository.get("name"),
        "visibility": visibility,
        "archived": archived,
        "collaborators": collaborators,
        "secret_leak_count": len(token_indicators),
        "severity": severity,
    }


def correlate_exposed_tokens(leaks: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge secret leak findings into a compact exposure summary."""
    token_total = sum(len(item.get("detected_secrets", [])) for item in leaks)
    repositories = [item.get("repository") for item in leaks if item.get("repository")]

    return {
        "affected_repositories": repositories,
        "token_count": token_total,
        "severity": "critical" if token_total else "info",
        "summary": f"{token_total} potentially exposed tokens detected across {len(repositories)} repositories.",
    }