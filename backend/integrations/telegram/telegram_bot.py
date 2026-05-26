import logging
from typing import Dict, Any, List
# import aiogram # Standard async telegram lib (placeholder for actual implementation)
from backend.integrations.telegram.telegram_templates import (
    render_p1_alert,
    render_approval_request,
    render_daily_digest,
    render_report_notification
)

logger = logging.getLogger(__name__)

class TelegramBotClient:
    """Manages Telegram bot operations and sending messages."""
    
    def __init__(self, token: str = None):
        self.token = token
        # self.bot = Bot(token=self.token) if token else None

    async def _send_message(self, user_id: str, text: str, reply_markup=None):
        if not self.token:
            logger.warning("Telegram bot token not configured. Skipping message.")
            return
        logger.info(f"Sending Telegram message to {user_id}")
        # await self.bot.send_message(chat_id=user_id, text=text, parse_mode='Markdown', reply_markup=reply_markup)

    async def send_p1_alert(self, user_id: str, finding_data: Dict[str, Any]):
        text = render_p1_alert(finding_data)
        # Inline keyboard with quick actions
        reply_markup = None 
        # reply_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="View in Platform", url="...")]])
        await self._send_message(user_id, text, reply_markup)

    async def send_scan_approval_request(self, user_id: str, request_data: Dict[str, Any]):
        text = render_approval_request(request_data)
        # Inline keyboard for Approve / Deny
        reply_markup = None
        # reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        #     [InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{request_data['approval_id']}")],
        #     [InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{request_data['approval_id']}")]
        # ])
        await self._send_message(user_id, text, reply_markup)

    async def send_daily_digest(self, user_id: str, digest_data: Dict[str, Any]):
        text = render_daily_digest(digest_data)
        await self._send_message(user_id, text)

    async def send_report_notification(self, user_id: str, report_data: Dict[str, Any]):
        text = render_report_notification(report_data)
        await self._send_message(user_id, text)

telegram_bot = TelegramBotClient()
