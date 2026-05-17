"""
Lightweight similarity utilities for findings.

Provides deterministic scoring functions for titles and endpoints.
"""
from __future__ import annotations

import math
import re
from typing import Tuple

from backend.core.fingerprint import normalize_endpoint, normalize_title


def _tokenize_text(s: str) -> set[str]:
    s = s or ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    tokens = set([t for t in s.split() if t])
    return tokens


def compare_titles(a: str | None, b: str | None) -> float:
    """Return title similarity between 0.0 and 1.0 using Jaccard token overlap."""
    if not a or not b:
        return 0.0
    ta = _tokenize_text(a)
    tb = _tokenize_text(b)
    if not ta or not tb:
        return 0.0
    inter = ta.intersection(tb)
    union = ta.union(tb)
    return len(inter) / len(union)


def compare_endpoints(a: str | None, b: str | None) -> float:
    """Compare endpoints; returns 0.0-1.0.

    Strategy:
    - Normalize endpoints
    - exact match -> 1.0
    - same host and similar path tokens -> high score
    """
    na = normalize_endpoint(a) if a else None
    nb = normalize_endpoint(b) if b else None
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0

    # split host and path
    def split_host_path(u: str) -> Tuple[str, str]:
        parts = u.split("/", 3)
        # parts: scheme:, '', host[:port], rest...
        host = parts[1] if len(parts) > 1 else ""
        # extract after host
        rest = "/".join(parts[2:]) if len(parts) > 2 else "/"
        return host, rest

    ha, pa = split_host_path(na)
    hb, pb = split_host_path(nb)
    score = 0.0
    if ha and hb and ha == hb:
        score += 0.5
    # token overlap on path
    ta = set([p for p in pa.split("/") if p])
    tb = set([p for p in pb.split("/") if p])
    if ta and tb:
        inter = ta.intersection(tb)
        union = ta.union(tb)
        score += 0.5 * (len(inter) / len(union))
    # clamp
    return max(0.0, min(1.0, score))


def calculate_similarity(title_a: str | None, endpoint_a: str | None, title_b: str | None, endpoint_b: str | None, severity_a: str | None = None, severity_b: str | None = None, weights: dict | None = None) -> float:
    """Calculate overall similarity in 0..1.

    Default weights: title 0.6, endpoint 0.3, severity 0.1
    """
    w = weights or {"title": 0.6, "endpoint": 0.3, "severity": 0.1}
    title_score = compare_titles(title_a, title_b)
    endpoint_score = compare_endpoints(endpoint_a, endpoint_b)
    severity_score = 1.0 if severity_a and severity_b and severity_a == severity_b else 0.0

    total = w["title"] * title_score + w["endpoint"] * endpoint_score + w["severity"] * severity_score
    # normalize by sum of weights
    s = sum(w.values())
    if s == 0:
        return 0.0
    return float(total / s)
