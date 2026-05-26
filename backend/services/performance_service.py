"""
Platform performance orchestration and optimization workflow service.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.cluster.worker_registry import WorkerRegistry
from backend.core.redis import get_redis
from backend.metrics.prometheus_metrics import prometheus_metrics
from backend.metrics.system_metrics import collect_system_metrics, detect_resource_pressure, summarize_system_health
from backend.observability.metrics_collector import aggregate_metrics, emit_metric_event
from backend.performance.cache_manager import cache_result, invalidate_cache, retrieve_cache
from backend.performance.query_optimizer import optimize_finding_queries, optimize_graph_queries, optimize_historical_lookups
from backend.performance.redis_optimizer import monitor_queue_depth, optimize_streams, reduce_event_pressure
from backend.performance.websocket_optimizer import batch_events, optimize_event_delivery, reduce_realtime_noise
from backend.optimization.ai_optimizer import compress_context, optimize_prompt, reduce_token_pressure
from backend.optimization.graph_optimizer import optimize_graph_payload, prioritize_high_signal_nodes, reduce_node_density
from backend.optimization.queue_optimizer import prioritize_high_signal_tasks, rebalance_queues, reduce_worker_idle_time
from backend.telemetry.ai_telemetry import summarize_ai_metrics
from backend.telemetry.websocket_telemetry import detect_connection_issues, monitor_connection_health
from backend.telemetry.worker_telemetry import detect_worker_bottlenecks, track_worker_load


class PerformanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.worker_registry = WorkerRegistry(db)

    async def analyze_platform_performance(self, organization_id: UUID) -> dict[str, Any]:
        org_id = str(organization_id)
        cached = await retrieve_cache(org_id, "performance", "analysis")
        if cached:
            return cached

        system = summarize_system_health()
        metrics = await aggregate_metrics(org_id)
        workers = await self.worker_registry.get_available_workers(org_id, limit=200)
        worker_summary = await track_worker_load(workers)
        worker_issues = detect_worker_bottlenecks(workers)
        websocket = await monitor_connection_health(org_id)
        websocket_issues = detect_connection_issues(org_id)
        ai_metrics = summarize_ai_metrics(org_id)
        queue_depth = await self._queue_depth(org_id)
        redis_pressure = monitor_queue_depth({"cluster_jobs": queue_depth})
        graph_summary = optimize_graph_payload({"nodes": [], "edges": [], "max_nodes": 100})

        health_score = self._health_score(system, websocket, ai_metrics, redis_pressure, worker_summary)
        summary = {
            "organization_id": org_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health_score": health_score,
            "system": system,
            "metrics": metrics,
            "workers": worker_summary,
            "worker_issues": worker_issues,
            "websocket": websocket,
            "websocket_issues": websocket_issues,
            "ai": ai_metrics,
            "redis": {
                "queue_depth": queue_depth,
                **redis_pressure,
            },
            "graph": graph_summary,
        }
        await cache_result(org_id, "performance", "analysis", summary, ttl_seconds=30)
        await emit_metric_event("performance.health_score", health_score, organization_id=org_id, labels={"component": "platform"})
        return summary

    async def optimize_runtime_behavior(self, organization_id: UUID, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        org_id = str(organization_id)
        payload = payload or {}
        ai_plan = optimize_prompt(payload.get("prompt", ""), payload.get("context")) if payload.get("prompt") else {"prompt": "", "cacheable": True}
        token_plan = reduce_token_pressure(payload.get("messages", []), budget_tokens=int(payload.get("token_budget", 4000))) if payload.get("messages") else {"messages": [], "estimated_tokens": 0}
        graph_plan = optimize_graph_payload(payload.get("graph_payload"))
        queue_plan = rebalance_queues(payload.get("queues"))
        worker_plan = reduce_worker_idle_time(payload.get("workers", []), payload.get("tasks", []))
        ws_plan = optimize_event_delivery(payload.get("events", []))
        redis_plan = optimize_streams(payload.get("streams", {}))

        return {
            "organization_id": org_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ai": {
                "prompt": ai_plan,
                "token_pressure": token_plan,
                "context_preview": compress_context(payload.get("context"))[:500],
            },
            "graph": {
                "optimized_payload": graph_plan,
                "high_signal_nodes": prioritize_high_signal_nodes(payload.get("graph_payload", {}).get("nodes", []) if payload.get("graph_payload") else []),
                "node_density_reduction": reduce_node_density(payload.get("graph_payload", {}).get("nodes", []) if payload.get("graph_payload") else [], max_nodes=100),
            },
            "queues": {
                "rebalance": queue_plan,
                "priority_tasks": prioritize_high_signal_tasks(payload.get("tasks", [])),
                "worker_idle_time": worker_plan,
            },
            "websocket": {
                "delivery": ws_plan,
                "batched_events": batch_events(payload.get("events", [])),
                "noise_reduced": reduce_realtime_noise(payload.get("events", [])),
            },
            "redis": redis_plan,
        }

    async def generate_performance_summary(self, organization_id: UUID) -> dict[str, Any]:
        org_id = str(organization_id)
        cached = await retrieve_cache(org_id, "performance", "summary")
        if cached:
            return cached

        overview = await self.analyze_platform_performance(organization_id)
        runtime = await self.optimize_runtime_behavior(organization_id, {})
        query_plans = {
            "findings": optimize_finding_queries({"organization_id": org_id, "include_related": True}),
            "graph": optimize_graph_queries({"organization_id": org_id}),
            "historical": optimize_historical_lookups({"organization_id": org_id}),
        }
        summary = {
            "organization_id": org_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overview": overview,
            "runtime": runtime,
            "query_plans": query_plans,
            "system_health": collect_system_metrics(),
        }
        await cache_result(org_id, "performance", "summary", summary, ttl_seconds=20)
        return summary

    async def get_websocket_metrics(self, organization_id: UUID) -> dict[str, Any]:
        overview = await self.analyze_platform_performance(organization_id)
        return {
            "organization_id": str(organization_id),
            "websocket": overview.get("websocket", {}),
            "issues": overview.get("websocket_issues", []),
            "recent_events": overview.get("metrics", {}).get("recent_events", []),
        }

    async def get_ai_metrics(self, organization_id: UUID) -> dict[str, Any]:
        overview = await self.analyze_platform_performance(organization_id)
        return {
            "organization_id": str(organization_id),
            "ai": overview.get("ai", {}),
            "recommendations": [
                "compress prompts before sending",
                "reuse cached AI outputs when context fingerprint matches",
                "drop stale conversation history outside the active task window",
            ],
        }

    async def get_queue_metrics(self, organization_id: UUID) -> dict[str, Any]:
        org_id = str(organization_id)
        queue_depth = await self._queue_depth(org_id)
        overview = await self.analyze_platform_performance(organization_id)
        return {
            "organization_id": org_id,
            "redis": overview.get("redis", {}),
            "queue_depth": queue_depth,
            "queue_pressure": monitor_queue_depth({"cluster_jobs": queue_depth}),
            "worker_idle_time": reduce_worker_idle_time(overview.get("workers", {}).get("workers", []), []),
        }

    async def get_graph_metrics(self, organization_id: UUID) -> dict[str, Any]:
        overview = await self.analyze_platform_performance(organization_id)
        graph = overview.get("graph", {})
        return {
            "organization_id": str(organization_id),
            "graph": graph,
            "recommendations": graph.get("recommendations", []),
        }

    async def invalidate_performance_cache(self, organization_id: UUID) -> dict[str, Any]:
        org_id = str(organization_id)
        return await invalidate_cache(org_id, "performance")

    async def _queue_depth(self, organization_id: str) -> int:
        try:
            redis_client = await get_redis()
            return int(await redis_client.zcard(f"cluster_jobs:{organization_id}"))
        except Exception:
            return 0

    def _health_score(
        self,
        system: dict[str, Any],
        websocket: dict[str, Any],
        ai_metrics: dict[str, Any],
        redis_pressure: dict[str, Any],
        worker_summary: dict[str, Any],
    ) -> float:
        system_score = max(0.0, 1.0 - float(system.get("pressure_score", 0.0)))
        websocket_score = 1.0 if websocket.get("healthy") else 0.6
        ai_score = 1.0 if ai_metrics.get("provider_health") else 0.85
        redis_score = 1.0 - float(redis_pressure.get("backlog_pressure", 0.0))
        worker_score = float(worker_summary.get("average_health", 0.0) or 0.0)
        score = (system_score + websocket_score + ai_score + redis_score + worker_score) / 5.0
        return round(max(0.0, min(1.0, score)), 3)
