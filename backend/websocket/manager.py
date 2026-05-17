"""
WebSocket connection manager.

Tracks per-user WebSocket connections and ties into a Redis-backed pub/sub listener.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Set

from fastapi import WebSocket

from backend.websocket import pubsub

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        # Map user_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        # Map user_id -> asyncio.Task running the Redis listener
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            conns = self._connections.setdefault(user_id, set())
            conns.add(websocket)
            logger.debug("User %s connected, total=%d", user_id, len(conns))
            # Start pubsub listener for this user if not running
            if user_id not in self._tasks:
                task = asyncio.create_task(self._start_user_listener(user_id))
                self._tasks[user_id] = task

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            conns = self._connections.get(user_id)
            if not conns:
                return
            conns.discard(websocket)
            logger.debug("User %s disconnected, remaining=%d", user_id, len(conns))
            if len(conns) == 0:
                # Cancel pubsub listener
                task = self._tasks.pop(user_id, None)
                if task:
                    task.cancel()
                self._connections.pop(user_id, None)

    async def send_personal_message(self, websocket: WebSocket, message: dict) -> None:
        try:
            await websocket.send_json(message)
        except Exception:
            # let caller handle disconnect
            logger.exception("Failed sending personal message to websocket")

    async def broadcast_to_user(self, user_id: str, message: dict) -> None:
        """Send message to all active websockets for a user."""
        conns = self._connections.get(user_id, set())
        if not conns:
            return
        dead: Set[WebSocket] = set()
        for ws in set(conns):
            try:
                await ws.send_json(message)
            except Exception:
                logger.exception("Websocket send failed for user %s", user_id)
                dead.add(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    conns.discard(ws)
                if len(conns) == 0:
                    # Cancel associated task
                    task = self._tasks.pop(user_id, None)
                    if task:
                        task.cancel()
                    self._connections.pop(user_id, None)

    async def _start_user_listener(self, user_id: str) -> None:
        """Start Redis pub/sub listener that forwards events to user websockets."""
        try:
            await pubsub.subscribe_to_events(user_id, self.broadcast_to_user)
        except asyncio.CancelledError:
            logger.debug("User listener cancelled for %s", user_id)
        except Exception:
            logger.exception("User listener failed for %s", user_id)


manager = ConnectionManager()
