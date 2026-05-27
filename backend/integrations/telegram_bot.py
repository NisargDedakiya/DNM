import httpx, logging
from backend.core.config import settings

logger = logging.getLogger(__name__)

class TelegramBot:
    API = 'https://api.telegram.org/bot'

    async def _send(self, text: str) -> bool:
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return False  # Not configured — skip silently
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(
                    f'{self.API}{settings.telegram_bot_token}/sendMessage',
                    json={'chat_id': settings.telegram_chat_id, 'text': text, 'parse_mode': 'HTML'}
                )
                return r.status_code == 200
        except Exception as e:
            logger.error(f'Telegram send failed (non-fatal): {e}')
            return False  # NEVER raise — Telegram failure must not crash the app

    async def critical_alert(self, title: str, program: str, severity: str,
                              confidence: float, url: str) -> bool:
        return await self._send(
            f'🚨 <b>{severity.upper()} FOUND</b> '
            f'<b>Program:</b> {program} '
            f'<b>Finding:</b> {title} '
            f'<b>Confidence:</b> {int(confidence*100)}% '
            f'<b>URL:</b> {url[:80]} '
            f'<i>Open NisargHunter AI to verify and submit</i>'
        )

    async def daily_digest(self, stats: dict) -> bool:
        return await self._send(
            f'📊 <b>Daily Summary</b> '
            f'Critical: {stats.get("critical",0)} | High: {stats.get("high",0)} | Medium: {stats.get("medium",0)} '
            f'Submitted today: {stats.get("submitted",0)} '
            f'Pending review: {stats.get("pending",0)}'
        )

telegram = TelegramBot()
