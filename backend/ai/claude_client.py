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
    BACKOFF    = [2, 4, 8, 16]  # retry wait seconds

    def __init__(self):
        self._anthropic = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def analyze(self, prompt: str, system: str, max_tokens: int | None = None) -> str:
        mt = max_tokens or self.MAX_TOKENS
        last_error: Exception | None = None
        for delay in self.BACKOFF:
            try:
                resp = await self._anthropic.messages.create(
                    model=self.MODEL,
                    max_tokens=mt,
                    system=system,
                    messages=[{'role': 'user', 'content': prompt}]
                )
                return resp.content[0].text
            except anthropic.RateLimitError as e:
                last_error = e
                logger.warning(f'Claude rate limited — waiting {delay}s')
                await asyncio.sleep(delay)
            except anthropic.APIError as e:
                raise ClaudeAPIError(f'Anthropic API error: {e}')
        raise ClaudeAPIError(f'Max retries exceeded: {last_error}')

    async def analyze_json(self, prompt: str, system: str) -> dict | list:
        # Append strong JSON instruction
        sys_json = system.strip() + '  IMPORTANT: Return ONLY valid JSON. No markdown. No backticks. No explanation.'
        for attempt in range(2):
            try:
                text = await self.analyze(prompt, sys_json)
                text = text.strip()
                # Strip markdown code fences if model adds them
                if text.startswith('```'):
                    lines = text.split(' ')
                    end = -1 if lines[-1].strip() == '```' else len(lines)
                    text = ' '.join(lines[1:end])
                return json.loads(text.strip())
            except json.JSONDecodeError:
                if attempt == 0:
                    prompt = prompt + '  You MUST return ONLY a JSON object or array. No text before or after.'
                else:
                    raise ClaudeAPIError('Claude response could not be parsed as JSON after retry')

    async def stream(self, prompt: str, system: str) -> AsyncGenerator[str, None]:
        async with self._anthropic.messages.stream(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=system,
            messages=[{'role': 'user', 'content': prompt}]
        ) as stream:
            async for text_chunk in stream.text_stream:
                yield text_chunk

# Singleton — import from here everywhere
claude = ClaudeClient()
