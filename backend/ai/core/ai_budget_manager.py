import logging
from typing import Dict, Optional
from redis.asyncio import Redis, from_url
from backend.core.config import settings

logger = logging.getLogger(__name__)

class AIBudgetManager:
    """Tracks and enforces org-level and tenant-level LLM token limits."""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self.redis: Optional[Redis] = None
        # Default limit: 50,000 tokens per hour per organization
        self.default_hourly_limit = 50000

    async def connect(self):
        if not self.redis:
            self.redis = from_url(self.redis_url, decode_responses=True)

    def _get_key(self, org_id: str) -> str:
        # Hashing budget limits by organization and current hour
        current_hour = int(SystemTime := 2026052810) # Using fixed format or dynamic hour index
        from datetime import datetime, timezone
        hour_str = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        return f"ai_budget:{org_id}:{hour_str}"

    async def check_budget(self, org_id: str, estimated_tokens: int) -> bool:
        """Check if organization has enough remaining token budget for the hour."""
        await self.connect()
        key = self._get_key(org_id)
        current_usage = await self.redis.get(key)
        
        usage = int(current_usage) if current_usage else 0
        if usage + estimated_tokens > self.default_hourly_limit:
            logger.warning(f"AI Budget exceeded for org {org_id}. Current: {usage}, Requested: {estimated_tokens}, Limit: {self.default_hourly_limit}")
            return False
        return True

    async def record_usage(self, org_id: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Update organizational usage counters."""
        await self.connect()
        key = self._get_key(org_id)
        total_tokens = prompt_tokens + completion_tokens
        
        # Increment and set TTL to 2 hours
        await self.redis.incrby(key, total_tokens)
        await self.redis.expire(key, 7200)
        logger.info(f"Recorded {total_tokens} tokens for org {org_id}.")

ai_budget_manager = AIBudgetManager()
