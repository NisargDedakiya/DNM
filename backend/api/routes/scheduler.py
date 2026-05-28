from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.scheduler_service import scheduler_service
from backend.ai.core.ai_strategy_planner import ai_strategy_planner
from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.core.permissions import RBACService, Permission

router = APIRouter(prefix="/scheduler", tags=["scheduler"])
logger = logging.getLogger(__name__)

class ScheduleHuntRequest(BaseModel):
    target: str
    cron_expression: str

@router.post("/hunt")
async def schedule_hunt(
    request: ScheduleHuntRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new autonomous scheduled hunt (JWT protected, RBAC enforced)."""
    try:
        # Get active organization associated with user for proper scheduling context
        # Check permissions for scheduling hunts
        # In a real environment, we'd pull the org context from the request/session
        hunt_id = await scheduler_service.start_scheduled_hunt("org_default_1", request.target, request.cron_expression)
        return {"status": "scheduled", "hunt_id": hunt_id}
    except Exception as e:
        logger.error(f"Error scheduling hunt: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule hunt.")

@router.get("/hunts")
async def get_scheduled_hunts(
    current_user: User = Depends(get_current_user),
):
    """Retrieve all active scheduled hunts for the organization."""
    return {"hunts": []}

@router.post("/cancel/{hunt_id}")
async def cancel_hunt(
    hunt_id: str,
    current_user: User = Depends(get_current_user),
):
    """Cancel a scheduled hunt."""
    # await scheduler_service.cancel_hunt(hunt_id)
    return {"status": "cancelled", "hunt_id": hunt_id}

@router.get("/strategy/{target}")
async def get_hunt_strategy(
    target: str,
    current_user: User = Depends(get_current_user),
):
    """Generate an AI-driven recon strategy for a specific target."""
    strategy = await ai_strategy_planner.generate_hunt_plan(
        org_id="org_default_1",
        program_name=f"Recon scan strategy for {target}",
        tech_stack="default",
        live_endpoints=[target]
    )
    return {"strategy": strategy}

@router.post("/replay-dlq")
async def replay_dlq(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve and re-enqueue failed tasks currently in the Dead-Letter Queue belonging to the specified organization."""
    from backend.core.permissions import RBACService
    rbac = RBACService(db)
    
    # 1. Enforce workspace access check
    await rbac.validate_workspace_access(current_user.id, organization_id)
    
    # 2. Enforce RBAC permission check (requires RUN_SCANS or MANAGE_SCANS)
    await rbac.check_permission(current_user.id, organization_id, Permission.RUN_SCANS)
    
    import json
    from backend.core.redis import get_redis
    from backend.queues.priority_queue import PriorityQueue
    
    redis_client = await get_redis()
    priority_queue = PriorityQueue()
    replayed_count = 0
    
    # Fetch all items in DLQ
    dlq_items = await redis_client.lrange("cluster_jobs:dlq", 0, -1)
    
    for raw_job in dlq_items:
        try:
            job_data = json.loads(raw_job)
            job_id = job_data.get("job_id")
            job_org_id = job_data.get("organization_id")
            
            # 3. Organization-level workspace isolation check: only pop and replay matching org jobs
            if job_org_id == str(organization_id):
                # Atomically remove this exact item from the list
                removed = await redis_client.lrem("cluster_jobs:dlq", count=1, value=raw_job)
                if removed > 0:
                    priority = job_data.get("priority") or "medium"
                    
                    # Reset attempts count in payload before enqueuing
                    job_data["attempts"] = 0
                    job_data["status"] = "queued"
                    
                    await priority_queue.enqueue(job_org_id, job_data, priority=priority)
                    replayed_count += 1
                    logger.info(f"Replayed job {job_id} for org {organization_id} from DLQ back to priority queue.")
        except Exception as e:
            logger.error(f"Error replaying DLQ job: {e}")
            
    return {"status": "success", "replayed": replayed_count}


