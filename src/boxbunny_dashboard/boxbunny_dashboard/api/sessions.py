"""Training session data endpoints for BoxBunny Dashboard.

Provides access to current live session data, detailed session summaries,
and paginated session history. All data is per-user.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from boxbunny_dashboard.api.auth import get_current_user
from boxbunny_dashboard.db.manager import DatabaseManager

logger = logging.getLogger("boxbunny.dashboard.sessions")
router = APIRouter()


# ---- Pydantic models ----

class SessionSummary(BaseModel):
    session_id: str
    mode: str
    difficulty: str
    started_at: str
    ended_at: Optional[str] = None
    is_complete: bool = False
    rounds_completed: int = 0
    rounds_total: int = 0
    work_time_sec: int = 0
    rest_time_sec: int = 0


class SessionDetail(SessionSummary):
    config: Dict[str, Any] = {}
    summary: Dict[str, Any] = {}
    events: List[Dict[str, Any]] = []


class SessionHistoryResponse(BaseModel):
    sessions: List[SessionSummary]
    total: int
    page: int
    page_size: int


# ---- Helpers ----

def _get_db(request: Request) -> DatabaseManager:
    return request.app.state.db


def _parse_json_field(value: Optional[str]) -> Dict[str, Any]:
    """Safely parse a JSON string field."""
    if not value:
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}


def _row_to_summary(row: Dict[str, Any]) -> SessionSummary:
    return SessionSummary(
        session_id=row["session_id"],
        mode=row.get("mode", "training"),
        difficulty=row.get("difficulty", "beginner"),
        started_at=row.get("started_at", ""),
        ended_at=row.get("ended_at"),
        is_complete=bool(row.get("is_complete", False)),
        rounds_completed=row.get("rounds_completed", 0),
        rounds_total=row.get("rounds_total", 0),
        work_time_sec=row.get("work_time_sec", 0),
        rest_time_sec=row.get("rest_time_sec", 0),
    )


# ---- Endpoints ----

@router.get("/current")
async def get_current_session(
    request: Request,
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
) -> Dict[str, Any]:
    """Return the latest live session data (most recent incomplete session)."""
    username = user["username"]
    sessions = db.get_session_history(username, limit=1)
    if not sessions:
        return {"active": False, "session": None}

    latest = sessions[0]
    is_active = not bool(latest.get("is_complete", True))
    response: Dict[str, Any] = {
        "active": is_active,
        "session": _row_to_summary(latest).model_dump(),
    }

    # Include live state from WebSocket manager if available
    ws_manager = request.app.state.ws_manager
    state = ws_manager._state_buffer.get(username)
    if state and is_active:
        response["live_state"] = state

    return response


@router.get("/history", response_model=SessionHistoryResponse)
async def get_session_history(
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    mode: Optional[str] = Query(default=None),
) -> SessionHistoryResponse:
    """Return paginated training session history."""
    username = user["username"]
    # Fetch extra to determine total (SQLite doesn't have cheap COUNT with LIMIT)
    all_sessions = db.get_session_history(username, limit=1000, mode=mode)
    total = len(all_sessions)
    start = (page - 1) * page_size
    page_slice = all_sessions[start : start + page_size]

    return SessionHistoryResponse(
        sessions=[_row_to_summary(s) for s in page_slice],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session_detail(
    session_id: str,
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
) -> SessionDetail:
    """Return detailed data for a specific training session."""
    username = user["username"]
    detail = db.get_session_detail(username, session_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return SessionDetail(
        session_id=detail["session_id"],
        mode=detail.get("mode", "training"),
        difficulty=detail.get("difficulty", "beginner"),
        started_at=detail.get("started_at", ""),
        ended_at=detail.get("ended_at"),
        is_complete=bool(detail.get("is_complete", False)),
        rounds_completed=detail.get("rounds_completed", 0),
        rounds_total=detail.get("rounds_total", 0),
        work_time_sec=detail.get("work_time_sec", 0),
        rest_time_sec=detail.get("rest_time_sec", 0),
        config=_parse_json_field(detail.get("config_json")),
        summary=_parse_json_field(detail.get("summary_json")),
        events=detail.get("events", []),
    )
