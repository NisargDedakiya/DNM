"""
Central scope validation service used by scan APIs and worker pipelines.

Provides async entrypoints that combine scope validation, policy checks and rate limiting.
"""
from __future__ import annotations

from typing import Iterable, List, Optional
from urllib.parse import urlparse

from backend.core import policies, rate_limiter, scope_validator


async def validate_scan_target(
    target: str,
    scopes: Iterable[str],
    user_id: str,
    allowlist: Optional[List[str]] = None,
    rate_limit: Optional[int] = None,
    rate_window: int = 3600,
    concurrency_limit: Optional[int] = None,
    program_id: Optional[str] = None,
) -> dict:
    """Validate a single scan target.

    Raises ValueError on invalid or blocked targets.

    Returns a dict with normalized target information.
    """
    if not target:
        raise ValueError("empty target")

    # Normalize: if it's a URL, parse host
    parsed = urlparse(target) if "://" in target else None
    host = None
    is_url = False
    if parsed and parsed.hostname:
        host = parsed.hostname
        is_url = True
    else:
        host = target

    # Policy checks (blocks localhost/private IPs)
    # allowlist bypass only for explicit allowlisted entries
    if allowlist and host.strip().lower() in [a.lower() for a in allowlist]:
        pass
    else:
        policies.validate_scan_policy(host, allowlist=allowlist)

    # Scope validation: host must be within provided scopes
    if is_url:
        in_scope = scope_validator.validate_url_scope(target, scopes)
    else:
        in_scope = scope_validator.validate_domain_scope(host, scopes)

    if not in_scope:
        raise ValueError("target out of scope")

    # Rate limiting
    if rate_limit is not None:
        allowed = await rate_limiter.check_scan_limit(user_id, rate_limit, rate_window)
        if not allowed:
            raise ValueError("rate limit exceeded")
        # increment counter for the allowed scan
        await rate_limiter.increment_scan_counter(user_id, rate_window)

    # Concurrency slot
    if concurrency_limit is not None and program_id is not None:
        ok = await rate_limiter.acquire_concurrency_slot(program_id, concurrency_limit)
        if not ok:
            raise ValueError("concurrency limit reached for program")

    normalized = scope_validator.normalize_domain(host)
    return {"target": target, "host": normalized, "is_url": is_url}


async def enforce_scope(target: str, scopes: Iterable[str], user_id: str, **kwargs) -> dict:
    """Alias for validate_scan_target to clearly express enforcement semantics."""
    return await validate_scan_target(target, scopes, user_id, **kwargs)


async def validate_pipeline_targets(
    targets: Iterable[str], scopes: Iterable[str], user_id: str, **kwargs
) -> List[dict]:
    """Validate a list of targets for a pipeline run.

    Returns list of normalized target dicts. Raises on first invalid target.
    """
    validated: List[dict] = []
    for t in targets:
        validated.append(await validate_scan_target(t, scopes, user_id, **kwargs))
    return validated
