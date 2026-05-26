"""
Investigation discussion thread helpers.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.collaboration.comment_engine import create_comment, summarize_discussion
from backend.core.events import EventType
from backend.core.redis import get_redis
from backend.models.investigation import Investigation
from backend.models.investigation_comment import InvestigationComment
from backend.services.event_service import event_service


async def create_thread(
    db: AsyncSession,
    organization_id: str,
    title: str,
    severity: str = "medium",
    assigned_to: UUID | None = None,
    source_finding_id: UUID | None = None,
    summary: str | None = None,
    created_by_id: UUID | None = None,
) -> dict[str, Any]:
    """Create a new investigation thread/workspace."""
    investigation = Investigation(
        organization_id=str(organization_id),
        title=title,
        severity=severity,
        status="open",
        assigned_to=assigned_to,
        source_finding_id=source_finding_id,
        summary=summary,
        workflow_stage="open",
    )
    db.add(investigation)
    await db.flush()
    await event_service.emit_event(
        EventType.INVESTIGATION_THREAD_OPENED,
        str(organization_id),
        {
            "investigation_id": str(investigation.id),
            "title": title,
            "severity": severity,
            "source_finding_id": str(source_finding_id) if source_finding_id else None,
            "created_by_id": str(created_by_id) if created_by_id else None,
        },
    )
    return await retrieve_thread(db, investigation.id, organization_id)


async def add_comment(
    db: AsyncSession,
    investigation_id: UUID,
    author_id: UUID,
    content: str,
    parent_comment_id: UUID | None = None,
    ai_reasoning: str | None = None,
) -> dict[str, Any]:
    """Add a threaded comment to an investigation."""
    comment_data = create_comment(content, str(author_id), ai_reasoning=ai_reasoning)
    investigation = await db.get(Investigation, investigation_id)
    if not investigation:
        raise ValueError("investigation not found")

    comment = InvestigationComment(
        investigation_id=investigation_id,
        author_id=author_id,
        content=comment_data["content"],
        parent_comment_id=parent_comment_id,
        ai_reasoning=comment_data.get("ai_reasoning"),
        metadata_={"mentions": comment_data.get("mentions", [])},
    )
    db.add(comment)
    await db.flush()

    payload = {
        "investigation_id": str(investigation_id),
        "comment_id": str(comment.id),
        "author_id": str(author_id),
        "content": comment.content,
        "parent_comment_id": str(parent_comment_id) if parent_comment_id else None,
        "ai_reasoning": comment.ai_reasoning,
        "mentions": comment.metadata_ or {},
    }
    await _publish_thread_event(str(investigation.organization_id), investigation_id, payload)
    return payload


async def retrieve_thread(
    db: AsyncSession,
    investigation_id: UUID,
    organization_id: str | None = None,
) -> dict[str, Any]:
    """Fetch a thread with nested comments, evidence hints, and summary."""
    investigation = await db.get(Investigation, investigation_id)
    if not investigation:
        raise ValueError("investigation not found")
    if organization_id and str(investigation.organization_id) != str(organization_id):
        raise PermissionError("cross-org investigation access blocked")

    result = await db.execute(
        select(InvestigationComment).where(InvestigationComment.investigation_id == investigation_id).order_by(InvestigationComment.created_at.asc())
    )
    comments = result.scalars().all()
    tree = _build_comment_tree(comments)
    discussion_summary = await summarize_discussion([
        {
            "id": str(comment.id),
            "author_id": str(comment.author_id),
            "content": comment.content,
            "ai_reasoning": comment.ai_reasoning,
            "created_at": comment.created_at.isoformat(),
        }
        for comment in comments
    ]) if comments else {"summary": investigation.summary or "", "open_questions": [], "next_steps": [], "confidence": 0.0}

    return {
        "investigation": {
            "id": str(investigation.id),
            "organization_id": str(investigation.organization_id),
            "title": investigation.title,
            "severity": investigation.severity,
            "status": investigation.status,
            "assigned_to": str(investigation.assigned_to) if investigation.assigned_to else None,
            "summary": investigation.summary,
            "workflow_stage": investigation.workflow_stage,
            "created_at": investigation.created_at.isoformat(),
        },
        "comments": tree,
        "summary": discussion_summary,
    }


async def stream_thread_updates(investigation_id: UUID, organization_id: str) -> AsyncIterator[dict[str, Any]]:
    """Stream collaboration updates for websocket-style consumers."""
    redis_client = await get_redis()
    channel = f"collaboration:investigation:{organization_id}:{investigation_id}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message is None:
                await asyncio.sleep(0)
                continue
            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            try:
                yield json.loads(data)
            except Exception:
                continue
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


def _build_comment_tree(comments: list[InvestigationComment]) -> list[dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []
    children: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for comment in comments:
        node = {
            "id": str(comment.id),
            "investigation_id": str(comment.investigation_id),
            "author_id": str(comment.author_id),
            "content": comment.content,
            "ai_reasoning": comment.ai_reasoning,
            "mentions": (comment.metadata_ or {}).get("mentions", []),
            "created_at": comment.created_at.isoformat(),
            "children": [],
        }
        nodes[str(comment.id)] = node
        if comment.parent_comment_id:
            children[str(comment.parent_comment_id)].append(node)
        else:
            roots.append(node)

    for parent_id, child_nodes in children.items():
        if parent_id in nodes:
            nodes[parent_id]["children"] = child_nodes

    return roots


async def _publish_thread_event(org_id: str, investigation_id: UUID, payload: dict[str, Any]) -> None:
    redis_client = await get_redis()
    channel = f"collaboration:investigation:{org_id}:{investigation_id}"
    await redis_client.publish(channel, json.dumps(payload, default=str))
    await event_service.emit_event(EventType.INVESTIGATION_COMMENT_ADDED, org_id, payload)
