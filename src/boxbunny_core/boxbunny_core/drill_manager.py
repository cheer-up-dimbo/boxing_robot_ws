"""Drill session manager for BoxBunny.

Loads combo drill definitions from YAML, validates detected punch sequences
against expected combos, tracks accuracy/timing/streak, and publishes
drill progress events.  Covers 50 combos across Beginner/Intermediate/Advanced.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
import rclpy
from rclpy.node import Node

from boxbunny_core.constants import (
    Difficulty, PunchType, Services, SessionState as SSConst, Topics,
)
from boxbunny_msgs.msg import (
    ConfirmedPunch, DrillDefinition, DrillEvent, DrillProgress, SessionState,
)
from boxbunny_msgs.srv import StartDrill

logger = logging.getLogger("boxbunny.drill_manager")

_CODE_TO_NAME: Dict[str, str] = {
    "1": PunchType.JAB, "2": PunchType.CROSS, "3": PunchType.LEFT_HOOK,
    "4": PunchType.RIGHT_HOOK, "5": PunchType.LEFT_UPPERCUT, "6": PunchType.RIGHT_UPPERCUT,
}


class _ActiveDrill:
    """Mutable state for a drill in progress."""
    def __init__(self, defn: Dict[str, Any], tolerance_ms: float) -> None:
        self.name: str = defn["name"]
        self.combo: List[str] = [_CODE_TO_NAME.get(str(c), str(c)) for c in defn["combo"]]
        self.timing_ms: float = float(defn.get("timing_ms", 300))
        self.total_reps: int = int(defn.get("reps", 10))
        self.tolerance_s: float = tolerance_ms / 1000.0
        self.detected: List[str] = []
        self.punch_times: List[float] = []
        self.reps_completed: int = 0
        self.reps_missed: int = 0
        self.accuracy_sum: float = 0.0
        self.timing_sum: float = 0.0
        self.current_streak: int = 0
        self.best_streak: int = 0


class DrillManager(Node):
    """Manages combo drill sessions and validates punch sequences."""

    def __init__(self) -> None:
        super().__init__("drill_manager")
        self.declare_parameter("drills_yaml", "")
        self.declare_parameter("timing_tolerance_ms", 500.0)
        self._default_tolerance = float(self.get_parameter("timing_tolerance_ms").value)
        self._catalogue: Dict[str, Dict[str, Any]] = {}
        self._difficulty_params: Dict[str, Dict[str, Any]] = {}
        self._load_drills(self.get_parameter("drills_yaml").value)
        self._drill: Optional[_ActiveDrill] = None
        self._session_active: bool = False
        self._combo_start: float = 0.0
        self._pub_def = self.create_publisher(DrillDefinition, Topics.DRILL_DEFINITION, 10)
        self._pub_evt = self.create_publisher(DrillEvent, Topics.DRILL_EVENT, 10)
        self._pub_prog = self.create_publisher(DrillProgress, Topics.DRILL_PROGRESS, 10)
        self.create_subscription(ConfirmedPunch, Topics.PUNCH_CONFIRMED, self._on_punch, 50)
        self.create_subscription(SessionState, Topics.SESSION_STATE, self._on_session, 10)
        self.create_service(StartDrill, Services.START_DRILL, self._handle_start)
        self.create_timer(0.5, self._check_timeout)
        logger.info("Drill manager initialised (%d drills loaded)", len(self._catalogue))

    def _load_drills(self, yaml_path: str) -> None:
        """Load drill definitions from YAML config."""
        if not yaml_path:
            yaml_path = str(Path(__file__).resolve().parents[3] / "config" / "drills.yaml")
        path = Path(yaml_path)
        if not path.exists():
            logger.warning("Drills YAML not found: %s", yaml_path)
            return
        try:
            with open(path, "r") as fh:
                raw = yaml.safe_load(fh) or {}
        except Exception as exc:
            logger.error("Failed to parse drills YAML: %s", exc)
            return
        self._difficulty_params = raw.get("difficulty", {})
        for level in (Difficulty.BEGINNER, Difficulty.INTERMEDIATE, Difficulty.ADVANCED):
            for drill in raw.get(level, []):
                drill["difficulty"] = level
                self._catalogue[f"{level}/{drill['name']}"] = drill
        logger.info("Loaded %d drills", len(self._catalogue))

    def _handle_start(
        self, req: StartDrill.Request, resp: StartDrill.Response
    ) -> StartDrill.Response:
        """Handle StartDrill service -- begin a new drill session."""
        difficulty = req.difficulty or Difficulty.BEGINNER
        key = f"{difficulty}/{req.drill_name}"
        defn = self._catalogue.get(key)
        if defn is None:
            resp.success, resp.message = False, f"Drill not found: {key}"
            return resp
        tol = float(self._difficulty_params.get(difficulty, {}).get(
            "timing_tolerance_ms", self._default_tolerance))
        self._drill = _ActiveDrill(defn, tol)
        self._combo_start = 0.0
        msg = DrillDefinition()
        msg.drill_name = self._drill.name
        msg.difficulty = difficulty
        msg.combo_sequence = list(self._drill.combo)
        msg.total_combos = self._drill.total_reps
        msg.target_speed = self._drill.timing_ms
        self._pub_def.publish(msg)
        resp.success, resp.drill_id = True, key
        resp.message = f"Drill '{self._drill.name}' started ({self._drill.total_reps} reps)"
        logger.info("Drill started: %s (tolerance=%.0fms)", key, tol)
        return resp

    def _on_session(self, msg: SessionState) -> None:
        """Track session lifecycle."""
        self._session_active = msg.state == SSConst.ACTIVE
        if msg.state == SSConst.COMPLETE and self._drill is not None:
            self._drill = None

    def _on_punch(self, msg: ConfirmedPunch) -> None:
        """Process each confirmed punch against the active drill combo."""
        if self._drill is None or not self._session_active:
            return
        now = msg.timestamp if msg.timestamp > 0 else time.time()
        if not self._drill.detected:
            self._combo_start = now
            self._emit_event("combo_started", now)
        self._drill.detected.append(msg.punch_type)
        self._drill.punch_times.append(now)
        idx = len(self._drill.detected) - 1
        if idx < len(self._drill.combo) and self._drill.detected[idx] != self._drill.combo[idx]:
            self._finish(now, partial=True)
            return
        if len(self._drill.detected) >= len(self._drill.combo):
            self._finish(now, partial=False)

    def _finish(self, ts: float, *, partial: bool) -> None:
        """Score a completed or partial combo attempt."""
        d = self._drill
        if d is None:
            return
        accuracy = self._accuracy(d.combo, d.detected)
        timing = self._timing_score(d)
        if partial or accuracy < 0.5:
            evt = "combo_partial" if d.detected else "combo_missed"
            d.reps_missed += 1
            d.current_streak = 0
        else:
            evt = "combo_completed"
            d.reps_completed += 1
            d.accuracy_sum += accuracy
            d.timing_sum += timing
            d.current_streak += 1
            d.best_streak = max(d.best_streak, d.current_streak)
        self._emit_event(evt, ts, accuracy, timing, d.detected, d.combo)
        self._emit_progress(ts)
        d.detected, d.punch_times = [], []
        self._combo_start = 0.0
        if d.reps_completed + d.reps_missed >= d.total_reps:
            logger.info("Drill '%s' done: %d/%d, streak=%d",
                        d.name, d.reps_completed, d.reps_completed + d.reps_missed, d.best_streak)
            self._drill = None

    @staticmethod
    def _accuracy(expected: List[str], detected: List[str]) -> float:
        if not expected:
            return 1.0
        return sum(1 for e, d in zip(expected, detected) if e == d) / len(expected)

    @staticmethod
    def _timing_score(d: _ActiveDrill) -> float:
        if len(d.punch_times) < 2 or d.timing_ms <= 0:
            return 1.0
        target = d.timing_ms / 1000.0
        gaps = [d.punch_times[i + 1] - d.punch_times[i] for i in range(len(d.punch_times) - 1)]
        avg_err = sum(abs(g - target) for g in gaps) / len(gaps)
        return max(0.0, 1.0 - avg_err / max(target, 0.1))

    def _check_timeout(self) -> None:
        """Mark combo missed if no punch within tolerance."""
        if self._drill is None or self._combo_start == 0.0:
            return
        limit = len(self._drill.combo) * (self._drill.timing_ms / 1000.0) + self._drill.tolerance_s * 2
        if time.time() - self._combo_start > limit:
            self._finish(time.time(), partial=True)

    def _emit_event(self, event_type: str, ts: float, accuracy: float = 0.0,
                    timing: float = 0.0, detected: Optional[List[str]] = None,
                    expected: Optional[List[str]] = None) -> None:
        """Publish a DrillEvent."""
        msg = DrillEvent()
        msg.timestamp, msg.event_type = ts, event_type
        msg.combo_index = (self._drill.reps_completed + self._drill.reps_missed) if self._drill else 0
        msg.accuracy, msg.timing_score = accuracy, timing
        msg.detected_punches, msg.expected_punches = detected or [], expected or []
        self._pub_evt.publish(msg)

    def _emit_progress(self, ts: float) -> None:
        """Publish a DrillProgress."""
        d = self._drill
        if d is None:
            return
        total = d.reps_completed + d.reps_missed
        msg = DrillProgress()
        msg.timestamp = ts
        msg.combos_completed = d.reps_completed
        msg.combos_remaining = max(0, d.total_reps - total)
        msg.overall_accuracy = d.accuracy_sum / d.reps_completed if d.reps_completed else 0.0
        msg.current_streak = float(d.current_streak)
        msg.best_streak = d.best_streak
        self._pub_prog.publish(msg)


def main(args: list[str] | None = None) -> None:
    """Entry point for the drill manager node."""
    rclpy.init(args=args)
    node = DrillManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
