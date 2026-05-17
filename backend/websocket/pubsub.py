"""
Redis pub/sub helpers for publishing and subscribing user-isolated events.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable

import redis.asyncio as redis

from backend.core.redis import get_redis

logger = logging.getLogger(__name__)


async def publish_event(user_id: str, event: dict) -> None:
    """Publish a JSON-serializable event to the user's channel."""
    r: redis.Redis = await get_redis()
    channel = f"user:{user_id}:events"
    payload = json.dumps(event, default=str)
    try:
        await r.publish(channel, payload)
        logger.debug("Published event to %s", channel)
    except Exception:
        logger.exception("Failed publishing event to %s", channel)


async def subscribe_to_events(user_id: str, forward_fn: Callable[[str, dict], None]) -> None:
    """
    Subscribe to a user's Redis channel and forward messages to `forward_fn`.

    This function runs until cancelled. `forward_fn` should be an async callable
    that accepts (user_id, message_dict).
    """
    r: redis.Redis = await get_redis()
    pubsub = r.pubsub()
    channel = f"user:{user_id}:events"
    await pubsub.subscribe(channel)
    logger.debug("Subscribed to channel %s", channel)

    try:
        while True:
            # get_message is non-blocking by default; use timeout to yield.
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message is None:
                await asyncio.sleep(0)  # yield to event loop
                continue
            # message is a dict with 'type', 'pattern', 'channel', 'data'
            try:
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                # parse json
                payload = json.loads(data)
            except Exception:
                logger.exception("Failed parsing pubsub payload for %s", channel)
                continue

            # Forward to manager's broadcast function
            try:
                await forward_fn(user_id, payload)
            except Exception:
                logger.exception("Forwarding event to websockets failed for %s", user_id)
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception:
            logger.exception("Error closing pubsub for %s", user_id)
        logger.debug("Unsubscribed and closed pubsub for %s", user_id)
