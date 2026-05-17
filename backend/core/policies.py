"""
Scan policy engine: dangerous target blocking and IP checks.

Functions provide deterministic, local checks only (no DNS resolution).
"""
from __future__ import annotations

import ipaddress
from typing import Optional

from backend.core.scope_validator import normalize_domain


def is_private_ip(addr: str) -> bool:
    """Return True if addr is a private/loopback/link-local/reserved IP.

    Accepts string IPv4/IPv6 addresses. If parsing fails, returns False.
    """
    try:
        ip = ipaddress.ip_address(addr)
    except Exception:
        return False

    # ipaddress properties: is_private, is_loopback, is_reserved, is_link_local, is_multicast
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)


def is_reserved_target(host: str) -> bool:
    """Return True if host is a reserved or internal-only target.

    This checks literal IP addresses and obvious hostnames like 'localhost' or '.local' domains.
    No DNS resolution is performed.
    """
    if not host:
        return True
    h = host.strip().lower()
    # obvious reserved names
    if h == "localhost" or h == "loopback":
        return True
    if h.startswith("127.") or h == "::1":
        return True
    if h.endswith(".local") or h.endswith(".internal"):
        return True

    # If it's an IP literal, detect private/reserved
    try:
        return is_private_ip(h)
    except Exception:
        return False


def validate_scan_policy(target: str, allowlist: Optional[list[str]] = None) -> None:
    """Validate a target (domain or IP) against safety policies.

    - Raises ValueError when the target is blocked.
    - allowlist: list of normalized domains/IPs that are explicitly allowed.

    This function performs local checks only and does not resolve DNS.
    """
    if not target:
        raise ValueError("empty target")

    al = [a.strip().lower() for a in (allowlist or [])]
    t = target.strip()

    # quick allowlist
    if t.lower() in al:
        return

    # check obvious hostnames
    low = t.lower()
    if low == "localhost" or low == "loopback" or low == "::1":
        raise ValueError("target blocked: localhost/loopback not allowed")

    # IP literal checks
    try:
        ip = ipaddress.ip_address(low)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError(f"target blocked: private or reserved IP {ip}")
        return
    except ValueError:
        # not an IP literal, continue
        pass

    # domain-level checks: normalize and detect single-label local names
    try:
        nd = normalize_domain(low)
    except Exception:
        raise ValueError("invalid domain")

    if nd == "localhost" or nd.endswith(".local"):
        raise ValueError("target blocked: local network name")

    # passed basic policy checks
    return
