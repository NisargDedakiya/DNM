"""
Organization-aware rate limiting and abuse prevention.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any
import asyncio


_REQUEST_HISTORY: dict[str, deque[datetime]] = defaultdict(deque)
_LOCK = asyncio.Lock()


def calculate_request_budget(organization_id: str, risk_level: str = "medium", activity_type: str = "api") -> dict[str, Any]:
    """Calculate a bounded request budget for a given org and activity type."""
    base_budget = 120 if activity_type == "websocket" else 180
    risk_factor = {"critical": 0.45, "high": 0.65, "medium": 1.0, "low": 1.25, "info": 1.5}.get(str(risk_level).lower(), 1.0)
    budget = max(10, int(base_budget * risk_factor))
    return {
        "organization_id": organization_id,
        "activity_type": activity_type,
        "risk_level": risk_level,
        "request_budget": budget,
        "window_seconds": 60,
    }


async def enforce_rate_limit(organization_id: str, activity_type: str = "api", risk_level: str = "medium") -> dict[str, Any]:
    """Apply org-scoped request budget enforcement."""
    budget = calculate_request_budget(organization_id, risk_level=risk_level, activity_type=activity_type)
    window = timedelta(seconds=budget["window_seconds"])
    now = datetime.utcnow()

    async with _LOCK:
        history = _REQUEST_HISTORY[organization_id]
        while history and now - history[0] > window:
            history.popleft()
        allowed = len(history) < budget["request_budget"]
        if allowed:
            history.append(now)

    return {
        **budget,
        "allowed": allowed,
        "requests_used": len(_REQUEST_HISTORY[organization_id]),
        "throttle_reason": None if allowed else "org_budget_exhausted",
    }


async def throttle_aggressive_activity(organization_id: str, activity_type: str = "scan", signal_strength: float = 0.0) -> dict[str, Any]:
    """Apply stronger throttling for bursts, scans, and websocket fanout."""
    budget = await enforce_rate_limit(organization_id, activity_type=activity_type, risk_level="high" if signal_strength >= 0.7 else "medium")
    aggressive = signal_strength >= 0.7 or budget["requests_used"] >= int(budget["request_budget"] * 0.8)
    return {
        **budget,
        "aggressive_activity": aggressive,
        "throttled": aggressive and not budget["allowed"],
        "recommended_delay_seconds": 30 if aggressive else 5,
    }