import logging
import json
from typing import Dict, Any, Optional
from backend.core.redis_streams import redis_streams
import uuid

logger = logging.getLogger(__name__)

class JobQueue:
    """Redis-backed async job queue for distributed task management."""
    
    QUEUE_NAME = "hunt_task_queue"

    async def enqueue_job(self, task_type: str, payload: Dict[str, Any], priority: int = 0) -> str:
        job_id = str(uuid.uuid4())
        job_data = {
            "job_id": job_id,
            "type": task_type,
            "priority": priority,
            "payload": payload,
            "status": "queued"
        }
        # In a real app, use Redis sorted sets for priority queue
        await redis_streams.publish_event(self.QUEUE_NAME, job_data)
        logger.info(f"Enqueued job {job_id} of type {task_type}")
        return job_id

    async def dequeue_job(self) -> Optional[Dict[str, Any]]:
        # In a real app, pop from the priority queue
        pass

    async def retry_job(self, job_id: str, payload: Dict[str, Any]):
        logger.info(f"Retrying job {job_id}")
        await self.enqueue_job("retry", payload, priority=1)

job_queue = JobQueue()
