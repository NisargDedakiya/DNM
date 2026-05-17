"""
WebSocket route for realtime events.

Endpoint: /ws?token=<jwt>
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt_handler import verify_token
from backend.database.session import get_db
from backend.models.user import User
from backend.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None, db: AsyncSession = Depends(get_db)) -> None:
    """WebSocket endpoint that authenticates via JWT query param and streams user events."""
    # Accept connection first to be able to close with a code
    await websocket.accept()

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_id = verify_token(token)
    except Exception:
        logger.warning("Invalid token on websocket connect")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Load user and ensure exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        logger.warning("User not found for websocket connect: %s", user_id)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Register connection
    await manager.manager.connect(user_id, websocket)
    logger.info("Websocket connected for user %s", user_id)

    try:
        # Keep connection open and react to incoming messages if needed
        while True:
            try:
                # wait for any incoming message to detect disconnects
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        await manager.manager.disconnect(user_id, websocket)
        logger.info("Websocket disconnected for user %s", user_id)
