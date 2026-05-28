import logging
import hashlib
import json
from typing import Optional
from redis.asyncio import Redis, from_url
from backend.core.config import settings

logger = logging.getLogger(__name__)

class AICache:
    """Redis-backed cache to reduce redundant AI generation."""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self.redis: Optional[Redis] = None

    async def connect(self):
        if not self.redis:
            self.redis = from_url(self.redis_url, decode_responses=True)

    def _generate_cache_key(self, prompt: str, system_prompt: str) -> str:
        content = f"{prompt}:{system_prompt}".encode('utf-8')
        return f"ai_cache:{hashlib.md5(content).hexdigest()}"

    async def cache_response(self, prompt: str, system_prompt: str, response: str):
        await self.connect()
        key = self._generate_cache_key(prompt, system_prompt)
        logger.debug(f"Caching AI response at {key}")
        try:
            await self.redis.set(key, response, ex=3600)  # 1 hour TTL
        except Exception as e:
            logger.error(f"Failed to write to AI cache: {e}")

    async def retrieve_cached_response(self, prompt: str, system_prompt: str) -> Optional[str]:
        await self.connect()
        key = self._generate_cache_key(prompt, system_prompt)
        try:
            response = await self.redis.get(key)
            if response:
                logger.info(f"AI Cache hit for key {key}")
                return response
        except Exception as e:
            logger.error(f"Failed to read from AI cache: {e}")
        return None

    async def invalidate_cache(self, key_pattern: str):
        await self.connect()
        logger.info(f"Invalidating AI cache for pattern {key_pattern}")
        try:
            keys = await self.redis.keys(key_pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to invalidate AI cache keys: {e}")

ai_cache = AICache()

