import logging
from typing import Dict, Any
from backend.core.events import EventType
from backend.services.event_service import event_service
# Database session dependency mock
# from backend.database.session import get_db

logger = logging.getLogger(__name__)

class TelegramHandlers:
    """Handles incoming callbacks and commands from Telegram."""

    async def validate_telegram_user(self, telegram_user_id: str) -> str:
        """Validate if the telegram user is linked to an organization."""
        # Query DB: db.query(TelegramSession).filter(telegram_user_id=telegram_user_id, is_active=True).first()
        # Return org_id if valid
        logger.info(f"Validating Telegram user {telegram_user_id}")
        return "org_default_1" # Mock

    async def handle_approval_callback(self, telegram_user_id: str, approval_id: str):
        """Process an approval action from inline buttons."""
        org_id = await self.validate_telegram_user(telegram_user_id)
        if not org_id:
            logger.error("Unauthorized approval attempt via Telegram.")
            return

        logger.info(f"Approval granted for {approval_id} by {telegram_user_id}")
        
        # Emit approval granted event to Redis for the worker to unblock
        await event_service.emit_event(
            EventType.APPROVAL_GRANTED,
            org_id,
            {"approval_id": approval_id, "status": "approved"}
        )

    async def handle_deny_callback(self, telegram_user_id: str, approval_id: str):
        """Process a deny action from inline buttons."""
        org_id = await self.validate_telegram_user(telegram_user_id)
        if not org_id:
            logger.error("Unauthorized deny attempt via Telegram.")
            return

        logger.info(f"Approval denied for {approval_id} by {telegram_user_id}")
        
        # Emit approval denied event
        await event_service.emit_event(
            EventType.APPROVAL_DENIED,
            org_id,
            {"approval_id": approval_id, "status": "denied"}
        )

telegram_handlers = TelegramHandlers()
