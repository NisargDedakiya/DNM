"""
Deterministic finding fingerprinting utilities.

Responsibilities:
- normalize endpoints (strip scheme, default ports, sort query params)
- normalize titles
- generate stable sha256 fingerprints for findings
"""
from __future__ import annotations

import hashlib
import re
from typing import Optional
from urllib.parse import parse_qsl, urlparse, urlunparse


_DEFAULT_PORTS = {"http": 80, "https": 443}


def normalize_endpoint(endpoint: Optional[str]) -> Optional[str]:
    """Normalize an endpoint/URL to a canonical string.

    - preserves host and path
    - removes default ports
    - sorts query parameters alphabetically
    - lowercases scheme and host
    - strips fragments
    Returns None when endpoint is falsy.
    """
    if not endpoint:
        return None
    endpoint = endpoint.strip()
    parsed = urlparse(endpoint) if "://" in endpoint else urlparse("//" + endpoint, scheme="http")
    scheme = (parsed.scheme or "http").lower()
    netloc = parsed.hostname.lower() if parsed.hostname else ""
    port = parsed.port
    if port and _DEFAULT_PORTS.get(scheme) == port:
        # omit default port
        port = None
    if port:
        netloc = f"{netloc}:{port}"

    path = parsed.path or "/"
    # collapse multiple slashes, remove trailing slash except root
    path = re.sub(r"/+", "/", path)
    if path != "/":
        path = path.rstrip("/")

    # sort query params
    q = parse_qsl(parsed.query, keep_blank_values=True)
    q_sorted = sorted(q)
    query = "&".join([f"{k}={v}" for k, v in q_sorted])

    normalized = urlunparse((scheme, netloc, path, "", query, ""))
    return normalized


def normalize_title(title: Optional[str]) -> Optional[str]:
    """Normalize a finding title for fingerprinting.

    - lowercases
    - strips punctuation
    - collapses whitespace
    """
    if not title:
        return None
    t = title.strip().lower()
    # remove punctuation except -_/.
    t = re.sub(r"[^a-z0-9\s\-_/\.]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def generate_finding_fingerprint(title: Optional[str], endpoint: Optional[str], severity: Optional[str] = None) -> str:
    """Generate a deterministic fingerprint for a finding.

    Combines normalized title + normalized endpoint + severity (optional) into sha256 digest.
    Returns hex string.
    """
    parts = []
    nt = normalize_title(title) or ""
    ne = normalize_endpoint(endpoint) or ""
    parts.append(nt)
    parts.append(ne)
    if severity:
        parts.append(severity.lower())

    payload = "||".join(parts)
    h = hashlib.sha256()
    h.update(payload.encode("utf-8"))
    return h.hexdigest()
