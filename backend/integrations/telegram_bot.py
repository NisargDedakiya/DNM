import httpx
import logging
from backend.core.config import settings

logger = logging.getLogger(__name__)

class TelegramBot:
    URL = 'https://api.telegram.org/bot'

    async def _send(self, text: str) -> bool:
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return False  # silently skip — bot not configured
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(
                    f'{self.URL}{settings.telegram_bot_token}/sendMessage',
                    json={'chat_id': settings.telegram_chat_id,
                          'text': text, 'parse_mode': 'HTML'}
                )
                return r.status_code == 200
        except Exception as e:
            logger.error(f'Telegram error: {e}')
            return False

    async def alert_critical(self, title: str, program: str,
                              severity: str, confidence: float, url: str) -> bool:
        return await self._send(
            f'🚨 <b>{severity.upper()} FOUND</b>\n'
            f'<b>Program:</b> {program}\n'
            f'<b>Finding:</b> {title}\n'
            f'<b>Confidence:</b> {int(confidence*100)}%\n'
            f'<b>URL:</b> {url[:80]}'
        )

    async def daily_digest(self, stats: dict) -> bool:
        return await self._send(
            f'📊 <b>Daily Summary</b>\n'
            f'Critical: {stats.get("critical",0)} | High: {stats.get("high",0)} | '
            f'Medium: {stats.get("medium",0)}\n'
            f'Submitted today: {stats.get("submitted",0)}\n'
            f'Pending review: {stats.get("pending",0)}'
        )

    async def scan_approved(self, program: str, tool: str, targets: int) -> bool:
        return await self._send(
            f'✅ <b>Scan Approved</b> {tool} on {targets} targets in {program}'
        )

telegram = TelegramBot()
