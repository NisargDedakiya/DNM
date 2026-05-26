"""
Token-efficient summarization helpers for hunt history.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


def _normalize_text(value: str) -> str:
    return " ".join((value or "").strip().split())


def compress_historical_context(context_items: list[dict[str, Any]], max_items: int = 8) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for item in context_items:
        summary = _normalize_text(str(item.get("summary") or item.get("title") or ""))
        if not summary:
            continue
        key = summary.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(summary)
        if len(lines) >= max_items:
            break
    return "\n".join(f"- {line}" for line in lines)


def summarize_hunt_history(history: list[dict[str, Any]]) -> dict[str, Any]:
    memory_types = Counter(item.get("memory_type", "unknown") for item in history)
    recurring = [
        {"memory_type": memory_type, "count": count}
        for memory_type, count in memory_types.items()
        if count > 1
    ]
    return {
        "total_items": len(history),
        "memory_type_counts": dict(memory_types),
        "recurring_patterns": recurring,
        "compressed_context": compress_historical_context(history),
    }


def summarize_recurring_risks(risk_items: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [float(item.get("risk_score", 0.0)) for item in risk_items if item.get("risk_score") is not None]
    latest_summary = _normalize_text(str(risk_items[0].get("summary", ""))) if risk_items else ""
    return {
        "total_snapshots": len(risk_items),
        "average_risk_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "latest_summary": latest_summary,
        "compressed_context": compress_historical_context(risk_items),
    }

