import asyncio
import json
from datetime import datetime, UTC
from uuid import UUID

TIMEOUT = 3600  # 1 hour
POLL    = 5     # seconds between polls

class ApprovalGate:

    @staticmethod
    async def request(
        scan_id: UUID,
        message: str,
        targets: list[str],
        tool: str,
        org_id: UUID,
    ) -> bool:
        from backend.core.redis import get_redis
        redis = await get_redis()

        req_key  = f'approval:req:{scan_id}'
        resp_key = f'approval:resp:{scan_id}'
        channel  = f'alerts:{org_id}'  # same channel Phase 16 monitoring uses

        payload = json.dumps({
            'event': 'approval_request',
            'scan_id': str(scan_id),
            'message': message,
            'targets_preview': targets[:5],
            'total_targets': len(targets),
            'tool': tool,
            'requested_at': datetime.now(UTC).isoformat(),
        })
        await redis.setex(req_key, TIMEOUT, payload)
        await redis.publish(channel, payload)  # triggers WebSocket → frontend modal

        # Poll for user response
        deadline = asyncio.get_event_loop().time() + TIMEOUT
        while asyncio.get_event_loop().time() < deadline:
            resp = await redis.get(resp_key)
            if resp:
                await redis.delete(resp_key)
                return json.loads(resp).get('approved', False)
            await asyncio.sleep(POLL)
        return False  # Safe default: deny on timeout

    @staticmethod
    async def respond(scan_id: UUID, approved: bool, user_id: UUID):
        from backend.core.redis import get_redis
        redis = await get_redis()
        await redis.setex(
            f'approval:resp:{scan_id}', 300,
            json.dumps({'approved': approved, 'user_id': str(user_id)})
        )
