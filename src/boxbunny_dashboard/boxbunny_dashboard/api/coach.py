"""Coach-mode endpoints for BoxBunny Dashboard.

Enables coaches to load presets, start/stop station sessions, and
monitor live participant stats.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from boxbunny_dashboard.api.auth import get_current_user
from boxbunny_dashboard.db.manager import DatabaseManager
from boxbunny_dashboard.websocket import ConnectionManager, EventType

logger = logging.getLogger("boxbunny.dashboard.coach")
router = APIRouter()


# ---- Pydantic models ----

class LoadConfigRequest(BaseModel):
    preset_id: int


class StartStationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    preset_id: Optional[int] = None
    config: Dict[str, Any] = {}


class EndSessionRequest(BaseModel):
    coaching_session_id: str


class ParticipantStats(BaseModel):
    username: str
    display_name: str
    rounds_completed: int = 0
    score: int = 0
    connected: bool = False


class CoachingSession(BaseModel):
    session_id: str
    name: str
    started_at: str
    ended_at: Optional[str] = None
    participant_count: int = 0


# ---- Helpers ----

def _get_db(request: Request) -> DatabaseManager:
    return request.app.state.db


def _get_ws(request: Request) -> ConnectionManager:
    return request.app.state.ws_manager


def _require_coach(user: dict) -> None:
    """Raise 403 if the user is not a coach."""
    if user.get("user_type") != "coach":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coach role required",
        )


# ---- Endpoints ----

@router.post("/load-config")
async def load_config(
    body: LoadConfigRequest,
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
    ws: ConnectionManager = Depends(_get_ws),
) -> Dict[str, Any]:
    """Load a preset as the active station configuration."""
    _require_coach(user)
    presets = db.get_presets(user["user_id"])
    preset = next((p for p in presets if p["id"] == body.preset_id), None)
    if preset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")

    db.increment_preset_use(body.preset_id)
    config_data = json.loads(preset["config_json"]) if preset["config_json"] else {}
    await ws.broadcast_to_role("coach", EventType.CONFIG_CHANGED, {
        "preset_id": body.preset_id,
        "config": config_data,
    })
    logger.info("Coach %s loaded preset %d", user["username"], body.preset_id)
    return {"loaded": True, "preset_id": body.preset_id, "config": config_data}


@router.post("/start-station")
async def start_station(
    body: StartStationRequest,
    user: dict = Depends(get_current_user),
    ws: ConnectionManager = Depends(_get_ws),
) -> Dict[str, Any]:
    """Start a coaching station session."""
    _require_coach(user)
    import secrets
    session_id = secrets.token_urlsafe(12)

    await ws.broadcast_to_role("individual", EventType.SESSION_STARTED, {
        "coaching_session_id": session_id,
        "name": body.name,
        "config": body.config,
    })
    logger.info("Coach %s started station: %s", user["username"], body.name)
    return {"coaching_session_id": session_id, "name": body.name, "started": True}


@router.post("/end-session")
async def end_session(
    body: EndSessionRequest,
    user: dict = Depends(get_current_user),
    ws: ConnectionManager = Depends(_get_ws),
) -> Dict[str, Any]:
    """End a coaching session."""
    _require_coach(user)
    await ws.broadcast_to_role("individual", EventType.SESSION_COMPLETED, {
        "coaching_session_id": body.coaching_session_id,
    })
    logger.info("Coach %s ended session %s", user["username"], body.coaching_session_id)
    return {"coaching_session_id": body.coaching_session_id, "ended": True}


@router.get("/live", response_model=List[ParticipantStats])
async def get_live_participants(
    user: dict = Depends(get_current_user),
    ws: ConnectionManager = Depends(_get_ws),
) -> List[ParticipantStats]:
    """Return live stats for connected participants."""
    _require_coach(user)
    connected_users = ws.get_connections_for_role("individual")
    stats: List[ParticipantStats] = []
    for uid in connected_users:
        state = ws._state_buffer.get(uid, {})
        stats.append(ParticipantStats(
            username=uid,
            display_name=state.get("display_name", uid),
            rounds_completed=state.get("rounds_completed", 0),
            score=state.get("score", 0),
            connected=True,
        ))
    return stats


@router.get("/sessions", response_model=List[Dict[str, Any]])
async def get_coaching_sessions(
    user: dict = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Return past coaching sessions (placeholder for future DB backing)."""
    _require_coach(user)
    # Future: query a coaching_sessions table
    return []
