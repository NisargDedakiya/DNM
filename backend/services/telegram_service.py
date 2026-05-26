import logging
from typing import Dict, Any, List
from backend.integrations.telegram.telegram_bot import telegram_bot
# Database session dependency mock for fetching active telegram IDs
# from backend.database.session import get_db

logger = logging.getLogger(__name__)

class TelegramService:
    """Centralized Telegram orchestration, consumes events and routes them."""

    def _get_active_subscribers(self, org_id: str) -> List[str]:
        """Fetch linked telegram_user_ids for the organization."""
        # Query DB: db.query(TelegramSession).filter(organization_id=org_id, is_active=True).all()
        return ["123456789"] # Mock ID

    async def notify_p1_finding(self, org_id: str, finding_data: Dict[str, Any]):
        """Route a P1 alert to all active Telegram users in the org."""
        subscribers = self._get_active_subscribers(org_id)
        logger.info(f"Routing P1 alert to {len(subscribers)} Telegram users for org {org_id}")
        
        for user_id in subscribers:
            await telegram_bot.send_p1_alert(user_id, finding_data)

    async def request_scan_approval(self, org_id: str, request_data: Dict[str, Any]):
        """Route an approval request (e.g., for sqlmap) to Telegram."""
        subscribers = self._get_active_subscribers(org_id)
        for user_id in subscribers:
            await telegram_bot.send_scan_approval_request(user_id, request_data)

    async def send_hunt_digest(self, org_id: str, digest_data: Dict[str, Any]):
        """Send daily digest."""
        subscribers = self._get_active_subscribers(org_id)
        for user_id in subscribers:
            await telegram_bot.send_daily_digest(user_id, digest_data)

    async def notify_report_ready(self, org_id: str, report_data: Dict[str, Any]):
        """Notify that a report is ready."""
        subscribers = self._get_active_subscribers(org_id)
        for user_id in subscribers:
            await telegram_bot.send_report_notification(user_id, report_data)

telegram_service = TelegramService()
