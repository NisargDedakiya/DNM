"""
Deterministic scope validation engine for scan authorization.

Responsibilities:
- normalize targets (domain/IP/URL)
- wildcard rule matching
- scope compatibility checks
- strict authorization decisions
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

_DOMAIN_RE = re.compile(r"^(?:[A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,63}$")


def _to_idna(host: str) -> str:
    return host.encode("idna").decode("ascii")


def normalize_target(target: str) -> str:
    """Normalize a scan target into canonical lowercase host representation."""
    if not target or not target.strip():
        raise ValueError("Target cannot be empty")

    raw = target.strip()
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").strip().lower().rstrip(".")

    if not host:
        raise ValueError("Target host could not be parsed")

    # Validate IP literals first.
    try:
        ip = ipaddress.ip_address(host)
        return str(ip)
    except ValueError:
        pass

    try:
        host_ascii = _to_idna(host)
    except Exception as exc:
        raise ValueError(f"Invalid host encoding: {host}") from exc

    if not _DOMAIN_RE.match(host_ascii):
        raise ValueError(f"Invalid domain format: {host_ascii}")

    return host_ascii


def match_scope_rule(normalized_target: str, scope_rule: str) -> bool:
    """Match normalized target host against one scope rule.

    Supported scope rules:
    - example.com (exact only)
    - *.example.com (subdomains only, not apex)
    """
    if not scope_rule or not scope_rule.strip():
        return False

    rule = scope_rule.strip().lower().rstrip(".")

    if rule.startswith("*."):
        base = normalize_target(rule[2:])
        if normalized_target == base:
            return False
        return normalized_target.endswith(f".{base}")

    return normalized_target == normalize_target(rule)


def is_authorized_target(target: str, scope_rules: list[str]) -> bool:
    """Return True when target is strictly authorized by provided scope rules."""
    normalized = normalize_target(target)

    if not scope_rules:
        return False

    return any(match_scope_rule(normalized, rule) for rule in scope_rules)


def validate_target(target: str, scope_rules: list[str]) -> dict[str, str | bool]:
    """Validate target against scope and return deterministic decision payload."""
    normalized = normalize_target(target)
    authorized = is_authorized_target(normalized, scope_rules)

    return {
        "target": target,
        "normalized_target": normalized,
        "authorized": authorized,
        "reason": "in_scope" if authorized else "out_of_scope",
    }
