import json
import logging
import asyncio
from typing import Dict, Any, AsyncGenerator, Optional
from redis.asyncio import Redis, from_url
from backend.core.config import settings
from backend.events.event_schema import BaseEvent, EventMetadata, EventType

logger = logging.getLogger(__name__)

class RedisEventBus:
    """Enterprise-grade Redis Stream-backed event bus supporting Acks, Dedup, and Retries."""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self.redis: Optional[Redis] = None

    async def connect(self) -> None:
        if not self.redis:
            self.redis = from_url(self.redis_url, decode_responses=True)

    async def disconnect(self) -> None:
        if self.redis:
            await self.redis.close()
            self.redis = None

    async def publish_event(self, stream_name: str, event: BaseEvent) -> str:
        """Publish a structured event into Redis Streams with deduplication tracking with retries."""
        for attempt in range(3):
            try:
                await self.connect()
                # Enforce deduplication window using Redis strings/hashes if desired, or relying on event_id check
                # For robustness, we save the event ID with a short TTL to support deduplication checks
                dedup_key = f"event_dedup:{event.event_id}"
                is_new = await self.redis.set(dedup_key, "1", ex=3600, nx=True)
                if not is_new:
                    logger.warning(f"Duplicate event detected and dropped: {event.event_id}")
                    return "duplicate"

                payload = {
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "org_id": event.org_id,
                    "user_id": event.user_id or "",
                    "timestamp": event.timestamp.isoformat(),
                    "metadata": json.dumps(event.metadata.model_dump()),
                    "payload": json.dumps(event.payload)
                }
                
                message_id = await self.redis.xadd(stream_name, payload)
                logger.info(f"Published event {event.event_id} ({event.event_type.value}) as stream message {message_id}")
                return message_id
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed to publish event: {e}. Reconnecting...")
                self.redis = None
                if attempt >= 2:
                    logger.error(f"Failed to publish event to Redis stream {stream_name} after 3 attempts.")
                    raise
                await asyncio.sleep(min(2 ** attempt, 5))

    async def subscribe_to_stream(self, stream_name: str, group_name: str) -> None:
        await self.connect()
        try:
            await self.redis.xgroup_create(stream_name, group_name, id='0', mkstream=True)
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Error creating consumer group: {e}")
                raise

    async def consume_events(self, stream_name: str, group_name: str, consumer_name: str) -> AsyncGenerator[BaseEvent, None]:
        """Generator delivering validated events from consumer groups with retries and acks."""
        while True:
            try:
                await self.connect()
                await self.subscribe_to_stream(stream_name, group_name)

                # Read new messages or pending items (xreadgroup)
                messages = await self.redis.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams={stream_name: '>'},
                    count=5,
                    block=2000
                )
                
                for stream, msgs in messages:
                    for message_id, data in msgs:
                        try:
                            # Reconstruct BaseEvent from hash fields
                            raw_meta = json.loads(data.get("metadata", "{}"))
                            metadata = EventMetadata(**raw_meta)
                            
                            event = BaseEvent(
                                event_id=data.get("event_id"),
                                event_type=EventType(data.get("event_type")),
                                org_id=data.get("org_id"),
                                user_id=data.get("user_id") or None,
                                timestamp=data.get("timestamp"),
                                metadata=metadata,
                                payload=json.loads(data.get("payload", "{}"))
                            )
                            
                            yield event
                            
                            # Acknowledge processed message
                            await self.redis.xack(stream_name, group_name, message_id)
                            # Clean stream message to maintain small storage footprint
                            await self.redis.xdel(stream_name, message_id)
                            
                        except Exception as parse_error:
                            logger.error(f"Failed to parse stream message {message_id}: {parse_error}")
                            # Ack bad payloads to avoid infinite loops on un-parsable entries
                            await self.redis.xack(stream_name, group_name, message_id)
                            
            except Exception as e:
                logger.error(f"Error consuming events from stream {stream_name}: {e}. Forcing reconnect...")
                self.redis = None
                await asyncio.sleep(2)

redis_event_bus = RedisEventBus()
