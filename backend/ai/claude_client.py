"""
Centralized Claude API client for safe, reusable AI workflows.

Design goals:
- async-first API calls
- prompt sanitization and redaction
- token-aware bounded requests
- deterministic structured parsing support
- unified error handling
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL_DEFAULT = "claude-3-5-sonnet-latest"
CLAUDE_TIMEOUT_SECONDS = 25.0
CLAUDE_MAX_RETRIES = 2
CLAUDE_MAX_PROMPT_CHARS = 14000


class ClaudeClientError(RuntimeError):
    """Raised when Claude communication fails in a non-recoverable way."""


class ClaudeClient:
    """Compatibility wrapper used by existing services expecting a client object."""

    async def query_async(
        self,
        prompt: str,
        *,
        organization_id: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 900,
        model: str = CLAUDE_MODEL_DEFAULT,
    ) -> str:
        response = await ask_claude(
            prompt,
            organization_id=organization_id,
            model=model,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        return response.get("text", "")

    async def structured_query_async(
        self,
        prompt: str,
        *,
        organization_id: str | None = None,
        required_keys: list[str] | None = None,
        model: str = CLAUDE_MODEL_DEFAULT,
    ) -> dict[str, Any]:
        return await generate_structured_response(
            prompt,
            organization_id=organization_id,
            required_keys=required_keys,
            model=model,
        )


def sanitize_prompt(prompt: str, organization_id: str | None = None) -> str:
    """Sanitize and constrain prompt text before sending to AI provider."""
    text = (prompt or "").strip()
    if not text:
        raise ValueError("Prompt cannot be empty")

    # Redact common secret patterns and auth material.
    patterns = [
        r"(?i)bearer\s+[a-z0-9\-\._~\+\/]+=*",
        r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+",
        r"(?i)authorization\s*[:=]\s*[^\s,;]+",
        r"(?i)cookie\s*[:=]\s*[^\s,;]+",
        r"AKIA[0-9A-Z]{16}",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "[REDACTED]", text)

    # Keep request bounded and deterministic.
    text = text[:CLAUDE_MAX_PROMPT_CHARS]

    # Add explicit safety framing to preserve advisory behavior.
    safety_header = (
        "You are a defensive security intelligence assistant. "
        "Do not provide exploit automation, credential abuse guidance, or destructive steps. "
        "Return advisory-only output for authorized scope validation and triage."
    )

    if organization_id:
        org_line = f"\nOrganization scope: {organization_id}"
    else:
        org_line = ""

    return f"{safety_header}{org_line}\n\n{text}"


def _estimate_max_input_tokens(sanitized_prompt: str) -> int:
    """Rough token estimate to enforce request bounds.

    Uses a conservative chars/4 approximation and clamps to upper bound.
    """
    estimated = max(1, len(sanitized_prompt) // 4)
    return min(estimated, 8000)


def handle_ai_error(exc: Exception) -> dict[str, Any]:
    """Normalize AI errors into a structured safe payload."""
    detail = str(exc)[:800]
    return {
        "success": False,
        "error": "claude_request_failed",
        "detail": detail,
    }


async def ask_claude(
    prompt: str,
    *,
    organization_id: str | None = None,
    model: str = CLAUDE_MODEL_DEFAULT,
    max_output_tokens: int = 900,
    temperature: float = 0.0,
    timeout_seconds: float = CLAUDE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Send a sanitized prompt to Claude and return normalized response data."""
    if not settings.anthropic_api_key:
        raise ClaudeClientError("Anthropic API key not configured")

    sanitized = sanitize_prompt(prompt, organization_id=organization_id)
    input_tokens_estimate = _estimate_max_input_tokens(sanitized)

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": model,
        "max_tokens": int(max(64, min(max_output_tokens, 2000))),
        "temperature": float(max(0.0, min(temperature, 0.3))),
        "messages": [{"role": "user", "content": sanitized}],
    }

    last_exc: Exception | None = None
    for attempt in range(CLAUDE_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(CLAUDE_API_URL, headers=headers, json=payload)
                response.raise_for_status()
                body = response.json()

            content_parts = body.get("content", [])
            text_parts = [part.get("text", "") for part in content_parts if isinstance(part, dict)]
            output_text = "\n".join([p for p in text_parts if p]).strip()

            return {
                "success": True,
                "model": body.get("model", model),
                "text": output_text,
                "raw": body,
                "usage": {
                    "input_tokens_estimate": input_tokens_estimate,
                    "output_tokens_max": payload["max_tokens"],
                    "provider_usage": body.get("usage", {}),
                },
            }
        except Exception as exc:  # pragma: no cover - network path
            last_exc = exc
            logger.warning("Claude call failed on attempt %d: %s", attempt + 1, exc)
            if attempt < CLAUDE_MAX_RETRIES:
                await asyncio.sleep(0.5 * (attempt + 1))

    raise ClaudeClientError(json.dumps(handle_ai_error(last_exc or RuntimeError("unknown"))))


async def generate_structured_response(
    prompt: str,
    *,
    organization_id: str | None = None,
    required_keys: list[str] | None = None,
    model: str = CLAUDE_MODEL_DEFAULT,
) -> dict[str, Any]:
    """Generate deterministic JSON-friendly response and validate required keys."""
    schema_hint = (
        "Return ONLY valid JSON object. "
        "No markdown, no prose outside JSON, no code fences."
    )
    if required_keys:
        schema_hint += f" Required top-level keys: {', '.join(required_keys)}."

    composed_prompt = f"{schema_hint}\n\n{prompt}"
    result = await ask_claude(
        composed_prompt,
        organization_id=organization_id,
        model=model,
        temperature=0.0,
    )

    text = result.get("text", "").strip()
    try:
        parsed = json.loads(text)
    except Exception as exc:
        raise ClaudeClientError(
            f"Failed to parse structured Claude response as JSON: {exc}"
        ) from exc

    if not isinstance(parsed, dict):
        raise ClaudeClientError("Structured response must be a JSON object")

    if required_keys:
        missing = [key for key in required_keys if key not in parsed]
        if missing:
            raise ClaudeClientError(f"Missing required keys in structured response: {missing}")

    return {
        "success": True,
        "data": parsed,
        "usage": result.get("usage", {}),
        "model": result.get("model", model),
    }
