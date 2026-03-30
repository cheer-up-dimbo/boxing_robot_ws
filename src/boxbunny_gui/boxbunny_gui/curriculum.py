"""Anki-style spaced repetition curriculum for boxing combos.

Manages a SQLite database of combos organised into difficulty levels and
groups.  Tracks mastery via rolling average of the last 5 scores and
supports group-based progression with automatic level-up detection.

Database schema (per-user copy of data/combos_template.db):
    combos: combo definitions + per-combo progress
    performance_history: individual session scores
"""
from __future__ import annotations

import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_WS_ROOT = Path(__file__).resolve().parents[3]  # boxing_robot_ws/
_TEMPLATE_DB = _WS_ROOT / "data" / "combos_template.db"

# Group boundaries per difficulty (start_idx, end_idx, group_name)
GROUP_BOUNDARIES: Dict[str, List[tuple]] = {
    "Beginner": [
        (1, 6, "Single Punches"),
        (7, 12, "2-Punch Combos with Jab"),
        (13, 15, "2-Punch Other Combos"),
    ],
    "Intermediate": [
        (1, 8, "3-Punch Combos"),
        (9, 11, "Body Shot Combos"),
        (12, 13, "Defense Combos"),
        (14, 20, "Advanced Patterns"),
    ],
    "Advanced": [
        (1, 5, "Long Combinations"),
        (6, 8, "Complex Defense"),
        (9, 15, "Counter Punching"),
    ],
}

MASTERY_THRESHOLDS: Dict[str, float] = {
    "Beginner": 3.0,
    "Intermediate": 4.0,
    "Advanced": 4.0,
}

MIN_ATTEMPTS_FOR_MASTERY = 5


def _combo_index(combo_id: str) -> int:
    """Extract numeric index from combo_id like 'beginner_003' -> 3."""
    try:
        return int(combo_id.rsplit("_", 1)[-1])
    except (ValueError, IndexError):
        return 0


class ComboCurriculum:
    """Manages boxing combo curriculum with Anki-style spaced repetition.

    Parameters
    ----------
    db_path : path to a user-specific combos database.
              If *None*, a temporary in-memory copy is used (guest mode).
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path
        self._conn = None  # sqlite3.Connection, set by _connect()
        self._connect()

    # ── Connection ──────────────────────────────────────────────────────

    def _connect(self) -> None:
        # Lazy import — avoids libstdc++ ABI conflict when Qt/ROS libs are loaded
        import sqlite3

        if self._db_path:
            path = Path(self._db_path)
            if not path.exists():
                self._copy_template(path)
            self._conn = sqlite3.connect(str(path))
        else:
            # Guest mode: temp file copy of template
            tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
            tmp.close()
            self._copy_template(Path(tmp.name))
            self._db_path = tmp.name
            self._conn = sqlite3.connect(tmp.name)
        self._conn.row_factory = sqlite3.Row
        logger.info("Curriculum DB connected: %s", self._db_path)

    @staticmethod
    def _copy_template(dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if _TEMPLATE_DB.exists():
            shutil.copy2(_TEMPLATE_DB, dest)
            logger.info("Copied combo template -> %s", dest)
        else:
            logger.warning("Combo template not found at %s", _TEMPLATE_DB)

    # ── Queries ─────────────────────────────────────────────────────────

    def get_combos_by_difficulty(self, difficulty: str) -> List[Dict[str, Any]]:
        """Return all combos for a difficulty level, ordered by combo_id."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT combo_id, combo_name, combo_sequence, difficulty_level,"
            " mastery_score, total_attempts, last_trained_timestamp"
            " FROM combos WHERE difficulty_level = ? ORDER BY combo_id",
            (difficulty,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_combo_by_id(self, combo_id: str) -> Optional[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT combo_id, combo_name, combo_sequence, difficulty_level,"
            " mastery_score, total_attempts, last_trained_timestamp"
            " FROM combos WHERE combo_id = ?",
            (combo_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    # ── Spaced repetition logic ─────────────────────────────────────────

    def get_next_combo(
        self, difficulty: str, last_combo_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Select the next combo to train using group-based progression.

        1. Find first group with unmastered combos.
        2. Within that group pick lowest-attempt combos.
        3. Avoid repeating *last_combo_id* when alternatives exist.
        4. Return None when all groups are mastered.
        """
        if difficulty not in GROUP_BOUNDARIES:
            return None

        threshold = MASTERY_THRESHOLDS.get(difficulty, 4.0)
        all_combos = self.get_combos_by_difficulty(difficulty)
        if not all_combos:
            return None

        def is_mastered(c: Dict[str, Any]) -> bool:
            return (
                (c.get("total_attempts") or 0) >= MIN_ATTEMPTS_FOR_MASTERY
                and (c.get("mastery_score") or 0.0) >= threshold
            )

        # Find first unfinished group
        active_group = None
        for start, end, _name in GROUP_BOUNDARIES[difficulty]:
            group = [
                c for c in all_combos
                if start <= _combo_index(c["combo_id"]) <= end
            ]
            if group and any(not is_mastered(c) for c in group):
                active_group = group
                break

        if not active_group:
            return None

        candidates = [c for c in active_group if not is_mastered(c)]
        if not candidates:
            return None

        # Lowest attempts first
        min_att = min((c.get("total_attempts") or 0) for c in candidates)
        lowest = sorted(
            [c for c in candidates if (c.get("total_attempts") or 0) == min_att],
            key=lambda c: c["combo_id"],
        )
        # Avoid immediate repeat
        non_repeat = [c for c in lowest if c["combo_id"] != last_combo_id]
        return non_repeat[0] if non_repeat else lowest[0]

    # ── Scoring ─────────────────────────────────────────────────────────

    def update_score(self, combo_id: str, score: float) -> bool:
        """Record a training score and update mastery average."""
        try:
            cur = self._conn.cursor()
            now = datetime.now().isoformat()

            cur.execute(
                "INSERT INTO performance_history (combo_id, timestamp, performance_score)"
                " VALUES (?, ?, ?)",
                (combo_id, now, score),
            )
            cur.execute(
                "SELECT performance_score FROM performance_history"
                " WHERE combo_id = ? ORDER BY timestamp DESC LIMIT 5",
                (combo_id,),
            )
            scores = [r["performance_score"] for r in cur.fetchall()]
            mastery = sum(scores) / len(scores) if scores else score

            cur.execute(
                "UPDATE combos SET mastery_score = ?, total_attempts = total_attempts + 1,"
                " last_trained_timestamp = ? WHERE combo_id = ?",
                (mastery, now, combo_id),
            )
            self._conn.commit()
            logger.info(
                "Score updated %s: score=%.1f mastery=%.2f (%d samples)",
                combo_id, score, mastery, len(scores),
            )
            return True
        except Exception:
            logger.exception("Failed to update score for %s", combo_id)
            self._conn.rollback()
            return False

    # ── Progress / stats ────────────────────────────────────────────────

    def get_combo_stats(self, combo_id: str) -> Optional[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT combo_name, combo_sequence, difficulty_level, total_attempts"
            " FROM combos WHERE combo_id = ?",
            (combo_id,),
        )
        row = cur.fetchone()
        if not row:
            return None

        cur.execute(
            "SELECT performance_score FROM performance_history"
            " WHERE combo_id = ? ORDER BY timestamp DESC LIMIT 5",
            (combo_id,),
        )
        last_5 = [r["performance_score"] for r in cur.fetchall()]
        last_5.reverse()
        avg = sum(last_5) / len(last_5) if last_5 else 0.0
        threshold = MASTERY_THRESHOLDS.get(row["difficulty_level"], 4.0)
        attempts = row["total_attempts"] or 0

        return {
            "combo_name": row["combo_name"],
            "combo_sequence": row["combo_sequence"],
            "last_5_scores": last_5,
            "average_score": avg,
            "total_attempts": attempts,
            "is_mastered": attempts >= MIN_ATTEMPTS_FOR_MASTERY and avg >= threshold,
            "threshold": threshold,
        }

    def get_level_progress(self, difficulty: str) -> Dict[str, Any]:
        """Get group-level progress for a difficulty tier."""
        threshold = MASTERY_THRESHOLDS.get(difficulty, 4.0)
        if difficulty not in GROUP_BOUNDARIES:
            return self._empty_progress(difficulty)

        all_combos = self.get_combos_by_difficulty(difficulty)
        combo_map = {}
        total = mastered = in_progress = struggling = 0
        for c in all_combos:
            total += 1
            att = c.get("total_attempts") or 0
            ms = c.get("mastery_score") or 0.0
            combo_map[c["combo_id"]] = {"attempts": att, "mastery": ms}
            if att < MIN_ATTEMPTS_FOR_MASTERY:
                in_progress += 1
            elif att >= MIN_ATTEMPTS_FOR_MASTERY and ms >= threshold:
                mastered += 1
            else:
                struggling += 1

        groups_done = 0
        cur_group_num = 0
        cur_group_name = "All groups mastered"
        cur_group_progress = "Complete"
        total_groups = len(GROUP_BOUNDARIES[difficulty])

        for idx, (start, end, name) in enumerate(GROUP_BOUNDARIES[difficulty], 1):
            ids = [
                cid for cid in combo_map
                if start <= _combo_index(cid) <= end
            ]
            g_total = len(ids)
            g_mastered = sum(
                1 for cid in ids
                if combo_map[cid]["attempts"] >= MIN_ATTEMPTS_FOR_MASTERY
                and combo_map[cid]["mastery"] >= threshold
            )
            if g_total > 0 and g_mastered == g_total:
                groups_done += 1
            elif cur_group_num == 0:
                cur_group_num = idx
                cur_group_name = name
                cur_group_progress = f"{g_mastered}/{g_total} combos mastered"

        can_level_up = groups_done == total_groups and total_groups > 0

        return {
            "difficulty": difficulty,
            "total_combos": total,
            "mastered_combos": mastered,
            "current_group_number": cur_group_num,
            "current_group_name": cur_group_name,
            "current_group_progress": cur_group_progress,
            "groups_completed": groups_done,
            "total_groups": total_groups,
            "can_level_up": can_level_up,
            "in_progress_combos": in_progress,
            "struggling_combos": struggling,
        }

    def check_progression_eligibility(self, difficulty: str) -> bool:
        """True if ALL combos at this difficulty are mastered."""
        if difficulty == "Advanced":
            return False
        progress = self.get_level_progress(difficulty)
        return progress["can_level_up"]

    @staticmethod
    def get_next_difficulty(current: str) -> Optional[str]:
        return {"Beginner": "Intermediate", "Intermediate": "Advanced"}.get(current)

    @staticmethod
    def _empty_progress(difficulty: str) -> Dict[str, Any]:
        return {
            "difficulty": difficulty, "total_combos": 0, "mastered_combos": 0,
            "current_group_number": 0, "current_group_name": "Unknown",
            "current_group_progress": "0/0", "groups_completed": 0,
            "total_groups": 0, "can_level_up": False,
            "in_progress_combos": 0, "struggling_combos": 0,
        }

    # ── Lifecycle ───────────────────────────────────────────────────────

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            logger.info("Curriculum DB closed")

    def __enter__(self) -> ComboCurriculum:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
