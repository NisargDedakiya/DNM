"""
Scope validation and normalization utilities.

Responsibilities:
- normalize domains and hosts
- validate URLs and domains
- wildcard scope matching (safe: *.example.com)
- subdomain matching

All functions are async-safe (no blocking I/O) and perform only local checks.
"""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import urlparse


_DOMAIN_RE = re.compile(r"^(?:[A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,63}$")
_SINGLE_LABEL_RE = re.compile(r"^[A-Za-z0-9-]{1,63}$")


def _to_ascii(domain: str) -> str:
    """Convert domain to ASCII (punycode) using the builtin IDNA codec.

    This avoids adding an external dependency.
    """
    # use Python's builtin idna codec
    return domain.encode("idna").decode("ascii")


def normalize_domain(candidate: str) -> str:
    """Normalize a domain or host string to its ASCII lowercase form.

    - strips trailing dots
    - lowercases
    - converts to IDNA (punycode) for non-ascii

    Raises ValueError for invalid domain formats.
    """
    if not candidate:
        raise ValueError("empty domain")
    # If candidate looks like a URL, extract netloc
    if "//" in candidate or ":/" in candidate:
        parsed = urlparse(candidate)
        host = parsed.hostname or ""
    else:
        host = candidate

    host = host.strip().lower().rstrip(".")
    if not host:
        raise ValueError("invalid host")

    # allow IP literals (validated elsewhere)
    if host.replace(".", "").isdigit():
        return host

    try:
        ascii_host = _to_ascii(host)
    except Exception as exc:  # UnicodeError, idna errors
        raise ValueError(f"invalid domain name: {host}") from exc

    # Simple validation: either single-label (localhost) or multi-label TLD
    if _DOMAIN_RE.match(ascii_host) or _SINGLE_LABEL_RE.match(ascii_host):
        return ascii_host

    raise ValueError(f"invalid domain format: {ascii_host}")


def _match_wildcard_scope(host: str, scope: str) -> bool:
    """Match host against wildcard scope like *.example.com.

    Wildcard only matches subdomains (not the apex). E.g. foo.example.com matches *.example.com, example.com does not.
    """
    assert scope.startswith("*.")
    base = scope[2:]
    # exact suffix match and ensure at least one subdomain label
    if host == base:
        return False
    return host.endswith("." + base)


def is_target_in_scope(target_host: str, scopes: Iterable[str]) -> bool:
    """Check whether normalized target_host is covered by any of the provided scopes.

    Scopes can be:
    - example.com (exact match + subdomains)
    - *.example.com (only subdomains)

    Notes:
    - target_host must be normalized (use normalize_domain)
    - scope strings will be normalized internally
    """
    try:
        host = normalize_domain(target_host)
    except ValueError:
        return False

    for s in scopes:
        if not s:
            continue
        s = s.strip().lower().rstrip(".")
        if s.startswith("*."):
            try:
                base = normalize_domain(s[2:])
            except ValueError:
                continue
            if _match_wildcard_scope(host, f"*.{base}"):
                return True
        else:
            try:
                norm = normalize_domain(s)
            except ValueError:
                continue
            # Exact match or any subdomain of norm (including apex)
            if host == norm:
                return True
            if host.endswith("." + norm):
                return True

    return False


def validate_url_scope(url: str, scopes: Iterable[str]) -> bool:
    """Validate a URL string is syntactically valid and in-scope.

    Returns True if URL host is in scope and host is a valid domain or IP.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("invalid URL")
    host = parsed.hostname
    if host is None:
        raise ValueError("invalid URL host")

    return is_target_in_scope(host, scopes)


def validate_domain_scope(domain: str, scopes: Iterable[str]) -> bool:
    """Validate a domain/host is syntactically valid and in-scope."""
    # normalize_domain will raise if invalid
    norm = normalize_domain(domain)
    return is_target_in_scope(norm, scopes)
