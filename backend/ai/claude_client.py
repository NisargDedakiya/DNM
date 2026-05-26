import anthropic
import asyncio
import json
import logging
from typing import AsyncGenerator
from backend.core.config import settings

logger = logging.getLogger(__name__)

class ClaudeAPIError(Exception):
    pass

class ClaudeClient:
    MODEL      = 'claude-sonnet-4-20250514'
    MAX_TOKENS = 4096
    RETRIES    = [2, 4, 8, 16]  # backoff seconds

    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def analyze(self, prompt: str, system: str,
                      max_tokens: int | None = None) -> str:
        mt = max_tokens or self.MAX_TOKENS
        for i, delay in enumerate(self.RETRIES):
            try:
                resp = await self._client.messages.create(
                    model=self.MODEL, max_tokens=mt, system=system,
                    messages=[{'role': 'user', 'content': prompt}]
                )
                return resp.content[0].text
            except anthropic.RateLimitError:
                if i == len(self.RETRIES)-1:
                    raise ClaudeAPIError('Rate limit exceeded')
                logger.warning(f'Rate limited, retrying in {delay}s')
                await asyncio.sleep(delay)
            except anthropic.APIError as e:
                raise ClaudeAPIError(str(e))

    async def analyze_json(self, prompt: str, system: str) -> dict | list:
        sys_with_json = system.strip() + '  IMPORTANT: Return ONLY valid JSON. No markdown fences. No preamble.'
        for attempt in range(2):
            try:
                text = await self.analyze(prompt, sys_with_json)
                text = text.strip()
                # Strip markdown fences if model adds them anyway
                if text.startswith('```'):
                    lines = text.split(' ')
                    text = ' '.join(lines[1:-1] if lines[-1]=='```' else lines[1:])
                return json.loads(text.strip())
            except json.JSONDecodeError:
                if attempt == 0:
                    prompt = prompt + '  Return ONLY a valid JSON object or array. Nothing else.'
                else:
                    raise ClaudeAPIError('Could not parse Claude response as JSON')

    async def stream(self, prompt: str, system: str) -> AsyncGenerator[str, None]:
        async with self._client.messages.stream(
            model=self.MODEL, max_tokens=self.MAX_TOKENS, system=system,
            messages=[{'role': 'user', 'content': prompt}]
        ) as s:
            async for chunk in s.text_stream:
                yield chunk

# Singleton — import this everywhere
claude = ClaudeClient()
