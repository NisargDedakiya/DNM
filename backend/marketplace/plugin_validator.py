"""
Plugin security validation and malicious pattern detection.
"""
from __future__ import annotations

import re
from typing import Any

HIGH_RISK_PATTERNS = [
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"subprocess\.",
    r"os\.system\(",
    r"socket\.",
    r"requests\.(get|post|put|delete|patch)",
    r"httpx\.",
    r"urllib\.",
    r"open\(",
]

SENSITIVE_PERMISSIONS = {"secrets", "workspace_private_data", "cross_org_data", "raw_attack_graphs"}


def inspect_plugin_permissions(manifest: dict[str, Any]) -> dict[str, Any]:
    permissions = [str(permission).lower() for permission in manifest.get("permissions", [])]
    denied = sorted(permission for permission in permissions if permission in SENSITIVE_PERMISSIONS)
    return {
        "permissions": permissions,
        "sensitive_permissions": denied,
        "permission_risk": "high" if denied else "low",
    }


def detect_malicious_patterns(manifest: dict[str, Any]) -> dict[str, Any]:
    source_text = " ".join(
        str(manifest.get(key) or "") for key in ["name", "version", "description"]
    ) + " " + " ".join(str(item) for item in manifest.get("dependencies", []))
    findings = []
    for pattern in HIGH_RISK_PATTERNS:
        if re.search(pattern, source_text, re.IGNORECASE):
            findings.append(pattern)
    return {
        "patterns": findings,
        "malicious": bool(findings),
    }


def validate_plugin_security(manifest: dict[str, Any]) -> dict[str, Any]:
    permissions = inspect_plugin_permissions(manifest)
    malicious = detect_malicious_patterns(manifest)
    approved = not permissions["sensitive_permissions"] and not malicious["malicious"]
    return {
        "approved": approved,
        "permissions": permissions,
        "malicious_patterns": malicious,
        "advisory_note": "Plugin execution remains sandboxed and org-scoped.",
    }
