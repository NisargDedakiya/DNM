"""
Structured comment engine for collaborative investigations.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.ai.client import AIClientError, generate_completion

logger = logging.getLogger(__name__)


_MENTION_PATTERN = re.compile(r"@([A-Za-z0-9_.-]{2,64})")


def mention_user(content: str) -> list[str]:
    """Extract username-style mentions from a comment body."""
    return list(dict.fromkeys(_MENTION_PATTERN.findall(content or "")))


def create_comment(content: str, author_id: str, ai_reasoning: str | None = None) -> dict[str, Any]:
    """Normalize a comment into structured collaboration metadata."""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", str(content or "")).strip()
    return {
        "author_id": str(author_id),
        "content": cleaned[:4000],
        "mentions": mention_user(cleaned),
        "ai_reasoning": (ai_reasoning or "").strip() or None,
    }


async def summarize_discussion(comments: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate an advisory summary of a discussion thread."""
    transcript = json.dumps(comments[-20:], default=str)[:4000]
    prompt = (
        "Summarize this collaborative security investigation discussion for analysts. "
        "Keep it concise, evidence-based, and advisory only. Return JSON with keys: "
        "summary, open_questions, next_steps, confidence.\n\n"
        f"DISCUSSION:\n{transcript}"
    )

    try:
        raw = await generate_completion(prompt, temperature=0.1)
        text = raw.get("completion") if isinstance(raw, dict) else str(raw)
        parsed = json.loads(text if isinstance(text, str) else str(text))
        return {
            "summary": parsed.get("summary", ""),
            "open_questions": parsed.get("open_questions", []),
            "next_steps": parsed.get("next_steps", []),
            "confidence": float(parsed.get("confidence", 0.0)),
        }
    except (AIClientError, ValueError, json.JSONDecodeError, Exception) as exc:
        logger.warning("Discussion summarization fallback used: %s", exc)
        top_comments = [item.get("content", "") for item in comments[-5:]]
        return {
            "summary": " ".join(top_comments)[:500],
            "open_questions": [],
            "next_steps": ["Review discussion and attach evidence"],
            "confidence": 0.0,
        }
