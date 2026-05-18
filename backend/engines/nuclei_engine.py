"""
Targeted Nuclei engine with fingerprint-aware template selection.
"""
from __future__ import annotations

from typing import Any

from backend.scanners.nuclei_scanner import NucleiScanner


FINGERPRINT_TEMPLATE_MAP: dict[str, list[str]] = {
    "wordpress": ["cves", "misconfiguration", "wordpress"],
    "nginx": ["misconfiguration", "exposures"],
    "apache": ["misconfiguration", "cves"],
    "graphql": ["graphql", "misconfiguration"],
    "jenkins": ["jenkins", "cves", "exposures"],
    "gitlab": ["gitlab", "cves", "misconfiguration"],
    "kubernetes": ["kubernetes", "exposures", "misconfiguration"],
    "default": ["misconfiguration", "exposures", "cves"],
}

SEVERITY_FLAGS = {
    "critical": ["-severity", "critical"],
    "high": ["-severity", "critical,high"],
    "medium": ["-severity", "critical,high,medium"],
    "low": ["-severity", "critical,high,medium,low"],
}


def select_templates_by_fingerprint(
    fingerprints: list[str],
    severity: str = "high",
) -> dict[str, Any]:
    """Select high-signal nuclei template categories from detected technologies."""
    selected: list[str] = []
    for fp in fingerprints:
        selected.extend(FINGERPRINT_TEMPLATE_MAP.get(fp.lower(), []))

    if not selected:
        selected = FINGERPRINT_TEMPLATE_MAP["default"].copy()

    # deterministic de-duplication
    selected = sorted(set(selected))

    return {
        "tags": selected,
        "severity": severity.lower(),
        "severity_flags": SEVERITY_FLAGS.get(severity.lower(), SEVERITY_FLAGS["high"]),
    }


async def run_targeted_nuclei_scan(
    target: str,
    fingerprints: list[str],
    severity: str = "high",
    timeout: int = 300,
) -> dict[str, Any]:
    """Execute nuclei scan with constrained tag/severity targeting to reduce noise."""
    scanner = NucleiScanner(timeout=timeout)
    template_plan = select_templates_by_fingerprint(fingerprints=fingerprints, severity=severity)

    # Prefer direct command here to inject tags/severity options safely.
    command = ["nuclei", "-u", scanner.sanitize_target(target), "-json"]

    if template_plan["tags"]:
        command.extend(["-tags", ",".join(template_plan["tags"])])

    command.extend(template_plan["severity_flags"])

    stdout, stderr = await scanner.execute_subprocess(command)
    findings = parse_nuclei_results(stdout)

    return {
        "target": target,
        "scanner": "nuclei",
        "template_plan": template_plan,
        "findings": findings,
        "count": len(findings),
        "stderr": stderr,
    }


def parse_nuclei_results(output: str) -> list[dict[str, Any]]:
    """Parse nuclei output into normalized high-signal finding objects."""
    from backend.scanners.parsers import parse_nuclei_output

    parsed = parse_nuclei_output(output)
    normalized: list[dict[str, Any]] = []

    for item in parsed:
        severity = str(item.get("severity") or "low").lower()
        normalized.append(
            {
                "title": item.get("name") or item.get("template_id") or "nuclei finding",
                "severity": severity,
                "endpoint": item.get("host"),
                "template_id": item.get("template_id"),
                "matched": item.get("matched"),
                "signal_score": 95 if severity == "critical" else 80 if severity == "high" else 60,
                "raw": item,
            }
        )

    return normalized
