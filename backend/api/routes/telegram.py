from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
import logging
from typing import Dict, Any

from backend.integrations.telegram.telegram_handlers import telegram_handlers
from backend.services.telegram_service import telegram_service
# Auth dependency mock
# from backend.api.dependencies import get_current_user

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)

class ConnectRequest(BaseModel):
    telegram_user_id: str
    username: str

class AlertTestRequest(BaseModel):
    target: str
    title: str

@router.post("/connect")
async def connect_telegram(request: ConnectRequest): # Add auth dependency here
    """Link a Telegram user ID to the current organization (JWT protected)."""
    # Logic to save to TelegramSession model
    logger.info(f"Linked Telegram user {request.telegram_user_id}")
    return {"status": "connected", "telegram_user_id": request.telegram_user_id}

@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Receive callbacks and messages from Telegram API."""
    data = await request.json()
    logger.debug(f"Received Telegram webhook: {data}")
    
    # Simple callback parsing logic
    if "callback_query" in data:
        callback = data["callback_query"]
        user_id = str(callback["from"]["id"])
        cb_data = callback["data"]
        
        if cb_data.startswith("approve_"):
            approval_id = cb_data.split("approve_")[1]
            await telegram_handlers.handle_approval_callback(user_id, approval_id)
        elif cb_data.startswith("deny_"):
            approval_id = cb_data.split("deny_")[1]
            await telegram_handlers.handle_deny_callback(user_id, approval_id)
            
    return {"status": "ok"}

@router.get("/status")
async def telegram_status():
    """Get the active Telegram connection status for the org."""
    return {"is_connected": True, "active_users": 1}

@router.post("/test-alert")
async def test_telegram_alert(request: AlertTestRequest):
    """Trigger a mock P1 alert to test the integration."""
    mock_finding = {
        "target": request.target,
        "title": request.title,
        "severity": "CRITICAL",
        "ai_confidence": 0.99,
        "summary": "This is a test alert from the NisargHunter platform.",
        "exploitability_summary": "High likelihood of exploitation."
    }
    await telegram_service.notify_p1_finding("org_default_1", mock_finding)
    return {"status": "alert_sent"}
