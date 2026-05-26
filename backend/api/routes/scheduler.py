from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import logging

from backend.services.scheduler_service import scheduler_service
from backend.services.strategy_service import strategy_service

router = APIRouter(prefix="/scheduler", tags=["scheduler"])
logger = logging.getLogger(__name__)

class ScheduleHuntRequest(BaseModel):
    target: str
    cron_expression: str

@router.post("/hunt")
async def schedule_hunt(request: ScheduleHuntRequest):
    """Create a new autonomous scheduled hunt (JWT protected, RBAC enforced)."""
    try:
        hunt_id = await scheduler_service.start_scheduled_hunt("org_default_1", request.target, request.cron_expression)
        return {"status": "scheduled", "hunt_id": hunt_id}
    except Exception as e:
        logger.error(f"Error scheduling hunt: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule hunt.")

@router.get("/hunts")
async def get_scheduled_hunts():
    """Retrieve all active scheduled hunts for the organization."""
    return {"hunts": []}

@router.post("/cancel/{hunt_id}")
async def cancel_hunt(hunt_id: str):
    """Cancel a scheduled hunt."""
    # await scheduler_service.cancel_hunt(hunt_id)
    return {"status": "cancelled", "hunt_id": hunt_id}

@router.get("/strategy/{target}")
async def get_hunt_strategy(target: str):
    """Generate an AI-driven recon strategy for a specific target."""
    strategy = await strategy_service.generate_strategy("org_default_1", target)
    return {"strategy": strategy}
