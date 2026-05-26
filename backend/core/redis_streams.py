import json
import logging
from typing import AsyncGenerator, Dict, Any
from redis.asyncio import Redis, from_url
from backend.core.config import settings

logger = logging.getLogger(__name__)

class RedisStreamManager:
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self.redis: Redis = None
        
    async def connect(self):
        if not self.redis:
            self.redis = from_url(self.redis_url, decode_responses=True)
            
    async def disconnect(self):
        if self.redis:
            await self.redis.close()

    async def publish_event(self, stream_name: str, event_data: Dict[str, Any]) -> str:
        """Publish an event to a Redis stream."""
        await self.connect()
        try:
            # Convert nested dicts to JSON strings for Redis hash fields
            payload = {k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v)) 
                       for k, v in event_data.items()}
            message_id = await self.redis.xadd(stream_name, payload)
            logger.debug(f"Published event {message_id} to stream {stream_name}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to publish event to {stream_name}: {e}")
            raise

    async def subscribe_to_stream(self, stream_name: str, group_name: str, consumer_name: str):
        """Create a consumer group if it doesn't exist."""
        await self.connect()
        try:
            await self.redis.xgroup_create(stream_name, group_name, id='0', mkstream=True)
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Error creating consumer group: {e}")
                raise

    async def consume_events(self, stream_name: str, group_name: str, consumer_name: str) -> AsyncGenerator[tuple, None]:
        """Consume events from a Redis stream securely."""
        await self.connect()
        await self.subscribe_to_stream(stream_name, group_name, consumer_name)
        
        while True:
            try:
                # Read from the stream
                messages = await self.redis.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams={stream_name: '>'},
                    count=10,
                    block=5000
                )
                
                for stream, msgs in messages:
                    for message_id, data in msgs:
                        # Reconstruct JSON objects
                        parsed_data = {}
                        for k, v in data.items():
                            try:
                                parsed_data[k] = json.loads(v)
                            except (ValueError, TypeError):
                                parsed_data[k] = v
                                
                        yield message_id, parsed_data
                        
                        # Acknowledge the message
                        await self.redis.xack(stream_name, group_name, message_id)
                        
            except Exception as e:
                logger.error(f"Error consuming events from {stream_name}: {e}")
                await asyncio.sleep(1) # Retry delay

redis_streams = RedisStreamManager()
