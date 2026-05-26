"""
Prompt and context compression helpers for AI-heavy workflows.
"""
from __future__ import annotations

from typing import Any


_SENSITIVE_KEYS = {"token", "access_token", "refresh_token", "authorization", "password", "secret", "api_key", "cookie"}


def optimize_prompt(prompt: str, context: dict[str, Any] | list[Any] | str | None = None, max_prompt_chars: int = 6000) -> dict[str, Any]:
    compact_context = compress_context(context)
    optimized_prompt = prompt.strip()
    if compact_context:
        optimized_prompt = f"{optimized_prompt}\n\nContext:\n{compact_context}"
    if len(optimized_prompt) > max_prompt_chars:
        optimized_prompt = optimized_prompt[: max_prompt_chars - 3].rstrip() + "..."
    return {
        "prompt": optimized_prompt,
        "original_char_count": len(prompt),
        "optimized_char_count": len(optimized_prompt),
        "estimated_savings": max(0, len(prompt) - len(optimized_prompt)),
        "cacheable": True,
    }


def compress_context(context: dict[str, Any] | list[Any] | str | None) -> str:
    if context is None:
        return ""
    if isinstance(context, str):
        text = " ".join(context.split())
        return text[:2000]
    if isinstance(context, list):
        items = [compress_context(item) for item in context]
        return "\n".join(item for item in items if item)
    if isinstance(context, dict):
        parts: list[str] = []
        for key, value in context.items():
            if str(key).lower() in _SENSITIVE_KEYS:
                continue
            compressed = compress_context(value)
            if compressed:
                parts.append(f"{key}: {compressed}")
        return " | ".join(parts)[:4000]
    return str(context)


def reduce_token_pressure(messages: list[dict[str, Any]], budget_tokens: int = 4000) -> dict[str, Any]:
    retained: list[dict[str, Any]] = []
    token_count = 0
    for message in messages:
        content = str(message.get("content", ""))
        estimated_tokens = max(1, len(content) // 4)
        if token_count + estimated_tokens > budget_tokens and message.get("role") != "system":
            continue
        retained.append({k: v for k, v in message.items() if str(k).lower() not in _SENSITIVE_KEYS})
        token_count += estimated_tokens
    return {
        "messages": retained,
        "estimated_tokens": token_count,
        "budget_tokens": budget_tokens,
        "cache_hit_opportunity": len(messages) - len(retained) == 0,
    }
