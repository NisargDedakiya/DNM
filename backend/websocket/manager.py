from typing import Dict, List, Any
from fastapi import WebSocket
import logging
import json

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Format: { org_id: { user_id: [websocket1, websocket2] } }
        self.active_connections: Dict[str, Dict[str, List[WebSocket]]] = {}

    async def connect(self, websocket: WebSocket, org_id: str, user_id: str):
        await websocket.accept()
        if org_id not in self.active_connections:
            self.active_connections[org_id] = {}
        if user_id not in self.active_connections[org_id]:
            self.active_connections[org_id][user_id] = []
            
        self.active_connections[org_id][user_id].append(websocket)
        logger.info(f"Client {user_id} connected to org {org_id}")

    def disconnect(self, websocket: WebSocket, org_id: str, user_id: str):
        if org_id in self.active_connections and user_id in self.active_connections[org_id]:
            if websocket in self.active_connections[org_id][user_id]:
                self.active_connections[org_id][user_id].remove(websocket)
            
            if not self.active_connections[org_id][user_id]:
                del self.active_connections[org_id][user_id]
            if not self.active_connections[org_id]:
                del self.active_connections[org_id]
                
        logger.info(f"Client {user_id} disconnected from org {org_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def send_to_org(self, org_id: str, message: Dict[str, Any]):
        """Broadcast an event to all users within a specific organization."""
        if org_id in self.active_connections:
            message_str = json.dumps(message)
            for user_id, connections in self.active_connections[org_id].items():
                for connection in connections:
                    try:
                        await connection.send_text(message_str)
                    except Exception as e:
                        logger.error(f"Error sending message to {user_id}: {e}")
                        self.disconnect(connection, org_id, user_id)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast to all connected clients (use carefully!)."""
        message_str = json.dumps(message)
        for org_id in list(self.active_connections.keys()):
            for user_id in list(self.active_connections[org_id].keys()):
                for connection in self.active_connections[org_id][user_id]:
                    try:
                        await connection.send_text(message_str)
                    except Exception as e:
                        logger.error(f"Error broadcasting message: {e}")
                        self.disconnect(connection, org_id, user_id)

websocket_manager = ConnectionManager()
