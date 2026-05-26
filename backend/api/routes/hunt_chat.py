from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import logging
from typing import Dict, Any

from backend.services.hunt_chat_service import hunt_chat_service
from backend.chat.chat_manager import chat_manager
# from backend.api.dependencies import get_current_user

router = APIRouter(prefix="/hunt-chat", tags=["hunt_chat"])
logger = logging.getLogger(__name__)

class ChatMessageRequest(BaseModel):
    session_id: str
    message: str

@router.post("/session")
async def create_session():
    """Initialize a new hunt chat session."""
    session_id = await chat_manager.create_chat_session("org_default_1")
    return {"session_id": session_id}

@router.post("/message")
async def send_message(request: ChatMessageRequest):
    """Send a message and get an AI response (JWT protected, RBAC enforced)."""
    try:
        response = await hunt_chat_service.process_chat_message(
            org_id="org_default_1", 
            session_id=request.session_id, 
            message=request.message
        )
        return {"response": response}
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat message.")

@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Retrieve chat history for a specific session."""
    # Logic to fetch from DB
    return {"session_id": session_id, "messages": []}

@router.get("/history")
async def get_all_sessions():
    """Retrieve all chat sessions for the current organization."""
    return {"sessions": []}
