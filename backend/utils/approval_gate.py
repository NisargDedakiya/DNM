import asyncio
import json
import logging
from datetime import datetime, UTC
from uuid import UUID

logger = logging.getLogger(__name__)
TIMEOUT = 3600  # 1 hour — user has 1 hour to approve
POLL_INTERVAL = 5  # seconds between checks

class ApprovalGate:

    @staticmethod
    async def request(
        scan_id: UUID,
        message: str,
        targets_preview: list[str],
        tool_name: str,
        organization_id: UUID,
    ) -> bool:
        from backend.core.redis import get_redis
        redis = await get_redis()

        req_key  = f'approval:req:{scan_id}'
        resp_key = f'approval:resp:{scan_id}'
        # Use same channel format as Phase 16 WebSocket alerts
        channel  = f'alerts:{organization_id}'

        payload = json.dumps({
            'event': 'approval_request',
            'scan_id': str(scan_id),
            'message': message,
            'targets_preview': targets_preview[:5],
            'total_targets': len(targets_preview),
            'tool': tool_name,
            'requested_at': datetime.now(UTC).isoformat(),
        })
        await redis.setex(req_key, TIMEOUT, payload)
        await redis.publish(channel, payload)

        # Poll until user responds or timeout
        loop = asyncio.get_event_loop()
        deadline = loop.time() + TIMEOUT
        while loop.time() < deadline:
            resp = await redis.get(resp_key)
            if resp:
                await redis.delete(resp_key)
                data = json.loads(resp)
                approved = data.get('approved', False)
                logger.info(f"Scan {scan_id} {'approved' if approved else 'denied'}")
                return approved
            await asyncio.sleep(POLL_INTERVAL)

        logger.warning(f'Scan {scan_id} approval timed out — defaulting to denied')
        return False  # Safe default: deny on timeout

    @staticmethod
    async def respond(scan_id: UUID, approved: bool, user_id: UUID):
        from backend.core.redis import get_redis
        redis = await get_redis()
        await redis.setex(
            f'approval:resp:{scan_id}',
            300,  # response valid for 5 minutes
            json.dumps({
                'approved': approved,
                'user_id': str(user_id),
                'responded_at': datetime.now(UTC).isoformat()
            })
        )
