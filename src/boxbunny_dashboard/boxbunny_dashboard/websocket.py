"""WebSocket connection manager for real-time dashboard sync.

Tracks connections by user_id and role, maintains a state buffer so
reconnecting clients receive the latest state immediately.
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("boxbunny.dashboard.ws")


class EventType(str, Enum):
    """Supported WebSocket event types."""
    SESSION_STARTED = "session_started"
    SESSION_STATS = "session_stats"
    SESSION_COMPLETED = "session_completed"
    CONFIG_CHANGED = "config_changed"
    USER_AUTHENTICATED = "user_authenticated"


class _ClientConnection:
    """Wraps a WebSocket with identity metadata."""

    __slots__ = ("ws", "user_id", "role", "connected_at")

    def __init__(self, ws: WebSocket, user_id: str, role: str) -> None:
        self.ws = ws
        self.user_id = user_id
        self.role = role
        self.connected_at = datetime.utcnow().isoformat()


class ConnectionManager:
    """Manage WebSocket connections, broadcasts, and state sync."""

    def __init__(self) -> None:
        self._connections: Dict[str, _ClientConnection] = {}
        self._state_buffer: Dict[str, Dict[str, Any]] = {}

    async def connect(
        self, ws: WebSocket, user_id: str, role: str = "individual",
    ) -> None:
        """Accept a WebSocket and register the client."""
        await ws.accept()
        conn_key = f"{user_id}:{id(ws)}"
        self._connections[conn_key] = _ClientConnection(ws, user_id, role)
        logger.info("WS connected: user=%s role=%s", user_id, role)

        # Send buffered state so reconnecting clients are caught up
        if user_id in self._state_buffer:
            await ws.send_json({
                "event": "state_sync",
                "data": self._state_buffer[user_id],
                "timestamp": datetime.utcnow().isoformat(),
            })

    def disconnect(self, ws: WebSocket, user_id: str) -> None:
        """Remove a WebSocket from the active connections."""
        conn_key: Optional[str] = None
        for key, conn in self._connections.items():
            if conn.ws is ws and conn.user_id == user_id:
                conn_key = key
                break
        if conn_key:
            del self._connections[conn_key]
            logger.info("WS disconnected: user=%s", user_id)

    async def send_to_user(
        self, user_id: str, event: str, data: Dict[str, Any],
    ) -> None:
        """Send a message to all connections for a specific user."""
        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        dead_keys: List[str] = []
        for key, conn in self._connections.items():
            if conn.user_id == user_id:
                try:
                    await conn.ws.send_json(message)
                except Exception:
                    dead_keys.append(key)
        for key in dead_keys:
            del self._connections[key]

    async def broadcast_to_role(
        self, role: str, event: str, data: Dict[str, Any],
    ) -> None:
        """Broadcast a message to all connections with a given role."""
        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        dead_keys: List[str] = []
        for key, conn in self._connections.items():
            if conn.role == role:
                try:
                    await conn.ws.send_json(message)
                except Exception:
                    dead_keys.append(key)
        for key in dead_keys:
            del self._connections[key]

    def update_state(self, user_id: str, state: Dict[str, Any]) -> None:
        """Update the state buffer for a user (used for reconnect sync)."""
        self._state_buffer[user_id] = state

    def get_connection_count(self) -> int:
        """Return total number of active connections."""
        return len(self._connections)

    def get_connections_for_role(self, role: str) -> List[str]:
        """Return user IDs connected with a given role."""
        return list({
            conn.user_id for conn in self._connections.values()
            if conn.role == role
        })


async def websocket_endpoint(ws: WebSocket) -> None:
    """Top-level WebSocket handler mounted on /ws."""
    manager: ConnectionManager = ws.app.state.ws_manager
    user_id = ws.query_params.get("user_id", "anonymous")
    role = ws.query_params.get("role", "individual")

    await manager.connect(ws, user_id, role)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"error": "invalid_json"})
                continue

            event = message.get("event")
            data = message.get("data", {})

            if event == "ping":
                await ws.send_json({"event": "pong"})
            elif event in {e.value for e in EventType}:
                manager.update_state(user_id, data)
                await manager.broadcast_to_role(role, event, data)
            else:
                await ws.send_json({"error": "unknown_event", "event": event})
    except WebSocketDisconnect:
        manager.disconnect(ws, user_id)
    except Exception:
        logger.exception("WebSocket error for user=%s", user_id)
        manager.disconnect(ws, user_id)
