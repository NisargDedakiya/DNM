"""
AI provider telemetry helpers.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from backend.metrics.prometheus_metrics import prometheus_metrics
from backend.observability.metrics_collector import emit_metric_event, record_metric

_TOKEN_USAGE: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=1000))
_LATENCY: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=1000))
_FAILURES: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=500))


async def track_token_usage(provider: str, model: str, prompt_tokens: int, completion_tokens: int, organization_id: str | None = None, cache_hit: bool = False, trace_id: str | None = None) -> dict[str, Any]:
    total = int(prompt_tokens) + int(completion_tokens)
    payload = {
        "provider": provider,
        "model": model,
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "total_tokens": total,
        "cache_hit": bool(cache_hit),
        "trace_id": trace_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    _TOKEN_USAGE[str(organization_id or "system")].append(payload)
    await emit_metric_event("ai.token_usage", total, organization_id=organization_id, labels={"provider": provider, "model": model, "cache_hit": cache_hit})
    return payload


async def monitor_ai_latency(provider: str, model: str, latency_ms: float, organization_id: str | None = None, success: bool = True, cache_hit: bool = False) -> dict[str, Any]:
    payload = {
        "provider": provider,
        "model": model,
        "latency_ms": float(latency_ms),
        "success": bool(success),
        "cache_hit": bool(cache_hit),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    org_key = str(organization_id or "system")
    _LATENCY[org_key].append(payload)
    if not success:
        _FAILURES[org_key].append(payload)
    await prometheus_metrics.observe_ai_latency(provider=provider, model=model, latency_ms=latency_ms, organization_id=organization_id, success=success)
    await record_metric("ai.latency_ms", latency_ms, organization_id=organization_id, labels={"provider": provider, "model": model, "success": success, "cache_hit": cache_hit})
    return payload


def detect_provider_failures(provider: str, organization_id: str | None = None) -> dict[str, Any]:
    org_key = str(organization_id or "system")
    latency_samples = list(_LATENCY[org_key])
    failure_samples = [sample for sample in _FAILURES[org_key] if sample.get("provider") == provider]
    provider_samples = [sample for sample in latency_samples if sample.get("provider") == provider]
    failure_rate = (len(failure_samples) / len(provider_samples)) if provider_samples else 0.0
    avg_latency = mean([float(sample.get("latency_ms", 0.0)) for sample in provider_samples]) if provider_samples else 0.0

    return {
        "provider": provider,
        "organization_id": organization_id,
        "failure_rate": round(failure_rate, 3),
        "avg_latency_ms": round(avg_latency, 3),
        "healthy": failure_rate < 0.2 and avg_latency < 3000,
        "recent_failures": list(failure_samples)[-5:],
    }


def summarize_ai_metrics(organization_id: str | None = None) -> dict[str, Any]:
    org_key = str(organization_id or "system")
    tokens = list(_TOKEN_USAGE[org_key])
    latency = list(_LATENCY[org_key])
    total_tokens = sum(int(item.get("total_tokens", 0)) for item in tokens)
    cache_hits = sum(1 for item in tokens if item.get("cache_hit"))
    avg_latency = mean([float(item.get("latency_ms", 0.0)) for item in latency]) if latency else 0.0
    providers = sorted({str(item.get("provider")) for item in latency + tokens if item.get("provider")})
    provider_health = [detect_provider_failures(provider, organization_id=organization_id) for provider in providers] if providers else []
    return {
        "organization_id": organization_id,
        "token_usage": {
            "count": len(tokens),
            "total_tokens": total_tokens,
            "cache_hits": cache_hits,
            "cache_hit_rate": round(cache_hits / len(tokens), 3) if tokens else 0.0,
            "recent": tokens[-10:],
        },
        "latency": {
            "count": len(latency),
            "avg_latency_ms": round(avg_latency, 3),
            "recent": latency[-10:],
        },
        "provider_health": provider_health,
    }
