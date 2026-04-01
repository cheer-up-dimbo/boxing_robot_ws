"""Simple in-memory session tracker for training history.

Guest sessions are stored in memory only (lost on close).
Logged-in users load/save from the database.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionTracker:
    """Tracks training/sparring/performance sessions."""

    def __init__(self) -> None:
        self._sessions: List[Dict[str, str]] = []

    def add_session(
        self,
        mode: str,
        duration: str = "--",
        punches: str = "0",
        score: str = "--",
    ) -> None:
        """Record a completed session."""
        session = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
            "mode": mode,
            "duration": duration,
            "punches": punches,
            "score": score,
        }
        self._sessions.insert(0, session)  # newest first
        logger.info("Session recorded: %s", session)

    @property
    def sessions(self) -> List[Dict[str, str]]:
        return list(self._sessions)

    def clear(self) -> None:
        self._sessions.clear()

    def load_for_user(self, username: str) -> None:
        """Load sessions from database for a logged-in user."""
        try:
            from boxbunny_gui.db_helper import get_user_by_username
            import sqlite3
            from pathlib import Path

            db_path = Path(__file__).resolve().parents[3] / "data" / "users" / username / "boxbunny.db"
            if not db_path.exists():
                self._sessions = []
                return

            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM training_sessions ORDER BY started_at DESC LIMIT 50"
            ).fetchall()
            conn.close()

            self._sessions = []
            for row in rows:
                self._sessions.append({
                    "date": row["started_at"][:10] if row["started_at"] else "--",
                    "time": row["started_at"][11:16] if row["started_at"] and len(row["started_at"]) > 11 else "",
                    "mode": row.get("mode", "Training"),
                    "duration": f"{row.get('duration_seconds', 0) // 60}m",
                    "punches": str(row.get("total_punches", 0)),
                    "score": f"{row.get('score', 0)}%",
                })
        except Exception as exc:
            logger.debug("Could not load user sessions: %s", exc)
            self._sessions = []


# Global singleton — shared across all pages
_tracker: Optional[SessionTracker] = None


def get_tracker() -> SessionTracker:
    """Get the global session tracker."""
    global _tracker  # noqa: PLW0603
    if _tracker is None:
        _tracker = SessionTracker()
    return _tracker


def reset_tracker() -> None:
    """Reset the tracker (e.g. on logout)."""
    global _tracker  # noqa: PLW0603
    _tracker = SessionTracker()
