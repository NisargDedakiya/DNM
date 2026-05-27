"""
Async AI client wrapper for Claude/OpenAI-compatible calls.

Provides centralized HTTP calls with timeout, simple retry, and error handling.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


DEFAULT_TIMEOUT = 20.0
MAX_RETRIES = 2


class AIClientError(RuntimeError):
    pass


async def generate_completion(prompt: str, model: str = "claude-v1", temperature: float = 0.0) -> dict:
    """Send prompt to AI provider and return parsed JSON response.

    This function is provider-agnostic; adjust headers/endpoint for your provider.
    It uses `settings.anthropic_api_key` for authentication when available.
    """
    api_key = settings.anthropic_api_key
    if not api_key:
        raise AIClientError("AI API key not configured")

    # Example Anthropic endpoint shape — adjust for your provider
    url = "https://api.anthropic.com/v1/complete"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens": 1000,
        "temperature": float(temperature),
    }

    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:  # pragma: no cover - network
            last_exc = exc
            logger.warning("AI request failed (attempt %d): %s", attempt + 1, exc)
            await asyncio.sleep(0.5 * (attempt + 1))

    raise AIClientError("AI request failed") from last_exc


async def analyze_finding(prompt: str) -> dict:
    """High-level analyze call returning structured dict.

    Returns provider raw JSON; callers must parse/validate.
    """
    return await generate_completion(prompt)


async def generate_report(prompt: str) -> dict:
    """Generate a report (structured content or markdown) using the AI.

    Returns provider raw JSON; callers should extract `completion` text.
    """
    return await generate_completion(prompt)


class ClaudeClient:
    def __init__(self):
        self.api_key = settings.anthropic_api_key

    async def create_message(
        self,
        model: str,
        max_tokens: int,
        temperature: float,
        system: str,
        messages: list[dict]
    ) -> str:
        if not self.api_key:
            return "Anthropic API key not configured."
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=self.api_key)
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages
        )
        if response.content:
            return response.content[0].text
        return ""
