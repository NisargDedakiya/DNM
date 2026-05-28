import logging
from typing import Dict, Any
from backend.observability.metrics_collector import record_metric

logger = logging.getLogger(__name__)

class AIMetrics:
    """Enterprise collector for AI latency, token counts, and hit rates."""

    @staticmethod
    async def record_latency(model: str, duration_seconds: float, org_id: str = None) -> None:
        labels = {"model": model, "metric_type": "latency"}
        await record_metric(
            name="ai_latency_seconds",
            value=duration_seconds,
            organization_id=org_id,
            labels=labels
        )
        logger.info(f"Recorded latency metric for model {model}: {duration_seconds}s")

    @staticmethod
    async def record_tokens(model: str, prompt_tokens: int, completion_tokens: int, org_id: str = None) -> None:
        total = prompt_tokens + completion_tokens
        labels = {"model": model, "metric_type": "tokens"}
        await record_metric(
            name="ai_total_tokens",
            value=float(total),
            organization_id=org_id,
            labels=labels
        )
        logger.info(f"Recorded token consumption: {total} tokens ({model})")

    @staticmethod
    async def record_cache_event(hit: bool, org_id: str = None) -> None:
        await record_metric(
            name="ai_cache_hit_ratio",
            value=1.0 if hit else 0.0,
            organization_id=org_id,
            labels={"event": "cache_hit" if hit else "cache_miss"}
        )
