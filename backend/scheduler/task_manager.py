import logging
from typing import Dict, Any
from backend.scheduler.job_queue import job_queue

logger = logging.getLogger(__name__)

class TaskManager:
    """Manages distributed task states and error handling."""

    VALID_STATES = ["queued", "running", "completed", "failed", "awaiting_approval"]

    async def update_task_state(self, job_id: str, new_state: str, metadata: Dict[str, Any] = None):
        if new_state not in self.VALID_STATES:
            raise ValueError(f"Invalid state: {new_state}")
            
        logger.info(f"Task {job_id} transition to {new_state}")
        # db.update(task, state=new_state)
        pass

    async def handle_task_failure(self, job_id: str, payload: Dict[str, Any], error: str):
        logger.error(f"Task {job_id} failed: {error}")
        await self.update_task_state(job_id, "failed", {"error": error})
        # Logic to decide whether to retry
        retry_count = payload.get("retry_count", 0)
        if retry_count < 3:
            payload["retry_count"] = retry_count + 1
            await job_queue.retry_job(job_id, payload)

task_manager = TaskManager()
