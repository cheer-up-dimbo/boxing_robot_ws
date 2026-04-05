"""Sparring engine for BoxBunny.

Generates unpredictable robot attack sequences using Markov-chain transition
matrices.  Five boxing styles (Boxer, Brawler, Counter-Puncher, Pressure,
Switch), three difficulty tiers, idle-surprise and block-reactive behaviours,
and weakness-bias targeting.
"""
from __future__ import annotations

import logging
import random
import time
from typing import Dict, List, Optional

import rclpy
from rclpy.node import Node

from boxbunny_core.constants import PunchType, SessionState as SSConst, Topics
from boxbunny_core.config_loader import load_config
from std_msgs.msg import String
from boxbunny_msgs.msg import ConfirmedPunch, PunchEvent, RobotCommand, SessionState

logger = logging.getLogger("boxbunny.sparring_engine")

PUNCH_CODES: List[str] = ["1", "2", "3", "4", "5", "6"]
PUNCH_NAMES: List[str] = [
    PunchType.JAB, PunchType.CROSS, PunchType.LEFT_HOOK,
    PunchType.RIGHT_HOOK, PunchType.LEFT_UPPERCUT, PunchType.RIGHT_UPPERCUT,
]
# Row/col order: jab, cross, l_hook, r_hook, l_uc, r_uc.  Rows sum to ~1.
STYLES: Dict[str, List[List[float]]] = {
    "boxer": [
        [.15, .30, .20, .15, .10, .10], [.25, .10, .25, .15, .10, .15],
        [.20, .25, .10, .15, .15, .15], [.20, .20, .15, .10, .15, .20],
        [.15, .25, .20, .15, .10, .15], [.20, .25, .15, .20, .10, .10],
    ],
    "brawler": [
        [.10, .15, .25, .25, .10, .15], [.10, .10, .25, .20, .15, .20],
        [.10, .15, .15, .20, .15, .25], [.10, .10, .25, .15, .20, .20],
        [.05, .15, .20, .20, .15, .25], [.05, .15, .25, .20, .20, .15],
    ],
    "counter_puncher": [
        [.25, .30, .15, .10, .10, .10], [.30, .15, .20, .10, .15, .10],
        [.25, .25, .10, .15, .10, .15], [.25, .20, .15, .10, .15, .15],
        [.20, .30, .15, .15, .10, .10], [.20, .30, .15, .10, .10, .15],
    ],
    "pressure": [
        [.30, .25, .15, .10, .10, .10], [.35, .15, .15, .15, .10, .10],
        [.30, .20, .10, .15, .10, .15], [.30, .20, .15, .10, .10, .15],
        [.25, .25, .15, .15, .10, .10], [.25, .25, .15, .10, .15, .10],
    ],
    "switch": [],  # resolved dynamically from other styles
}
DIFF_INTERVAL: Dict[str, float] = {"easy": 2.0, "medium": 1.2, "hard": 0.7}
IDLE_THRESHOLD_S = 3.0
WEAKNESS_BIAS = 0.08


class SparringEngine(Node):
    """Generates robot attack sequences via style-specific Markov chains."""

    def __init__(self) -> None:
        super().__init__("sparring_engine")
        self.declare_parameter("style", "boxer")
        self.declare_parameter("difficulty", "medium")
        self.declare_parameter("switch_interval_s", 20.0)
        self._style: str = self.get_parameter("style").value
        self._difficulty: str = self.get_parameter("difficulty").value
        self._switch_interval: float = self.get_parameter("switch_interval_s").value
        self._active: bool = False
        self._mode: str = ""  # "sparring" or "free"
        self._last_session_msg: float = 0.0  # watchdog: last SessionState received
        self._session_timeout_s: float = 5.0  # deactivate if no state msg for this long
        self._last_attack: float = 0.0
        self._last_user_punch: float = 0.0
        self._cur_idx: int = 0
        self._blocked_last: bool = False
        self._weakness: Dict[int, float] = {}
        self._switch_at: float = 0.0
        self._active_style: str = self._style

        # Free training / counter-punch config
        ft = load_config().free_training
        self._ft_counter_strikes: Dict[str, List[str]] = ft.pad_counter_strikes
        self._ft_cooldown_s: float = ft.counter_cooldown_ms / 1000.0
        self._ft_speed: str = ft.speed
        self._ft_last_counter: float = 0.0
        # Sparring counter-punch probability by difficulty
        self._counter_prob: Dict[str, float] = {"easy": 0.3, "medium": 0.5, "hard": 0.8}
        self._counters_enabled: bool = True
        # Robot busy flag — only one strike at a time
        self._robot_busy: bool = False
        # User-configured counter speed (None = use difficulty-based default)
        self._counter_speed_override: Optional[str] = None

        self._pub_cmd = self.create_publisher(RobotCommand, Topics.ROBOT_COMMAND, 10)
        self.create_subscription(SessionState, Topics.SESSION_STATE, self._on_session, 10)
        self.create_subscription(ConfirmedPunch, Topics.PUNCH_CONFIRMED, self._on_user_punch, 50)
        # Subscribe to IMU punch events for free training reactive mode
        self.create_subscription(PunchEvent, Topics.IMU_PUNCH_EVENT, self._on_imu_punch, 10)
        self.create_subscription(String, Topics.SESSION_CONFIG_JSON, self._on_session_config, 10)
        # Subscribe to strike feedback to know when arm is done
        self.create_subscription(String, Topics.ROBOT_STRIKE_FEEDBACK, self._on_strike_feedback, 10)
        self.create_timer(0.1, self._tick)
        logger.info("Sparring engine initialised (style=%s, difficulty=%s)",
                     self._style, self._difficulty)

    def _on_session(self, msg: SessionState) -> None:
        """Activate during sparring or free training sessions."""
        self._last_session_msg = time.time()
        was = self._active
        self._mode = msg.mode
        self._active = msg.state == SSConst.ACTIVE and msg.mode == "sparring"
        if self._active and not was:
            now = time.time()
            self._last_attack = now
            self._last_user_punch = now
            self._cur_idx = 0
            self._blocked_last = False
            self._switch_at = now
            self._active_style = self._style
            self._ft_last_counter = now  # prevent instant counter on first pad strike
            self._robot_busy = False
            self._counters_enabled = True  # default ON
            logger.info("Engine activated: mode=%s counters=%s",
                        msg.mode, self._counters_enabled)

    def _on_session_config(self, msg: String) -> None:
        """Read session config for style, difficulty, counters, and speed."""
        try:
            import json
            config = json.loads(msg.data)
            if "style" in config:
                style = config["style"].lower()
                if style in STYLES:
                    self._style = style
                    self._active_style = style
                    logger.info("Sparring style set to %s (from config)", style)
            if "difficulty" in config:
                diff = config["difficulty"].lower()
                if diff in DIFF_INTERVAL:
                    self._difficulty = diff
                    logger.info("Sparring difficulty set to %s (from config)", diff)
            if "counters_enabled" in config:
                self._counters_enabled = bool(config["counters_enabled"])
                logger.info("Sparring counters %s (from config)",
                            "enabled" if self._counters_enabled else "disabled")
            if "counter_speed" in config:
                self._counter_speed_override = config["counter_speed"]
                logger.info("Counter speed override: %s", self._counter_speed_override)
        except Exception:
            pass

    def set_counters_enabled(self, enabled: bool) -> None:
        """Toggle reactive counter-punches in sparring mode."""
        self._counters_enabled = enabled
        logger.info("Sparring counters %s", "enabled" if enabled else "disabled")

    def _on_strike_feedback(self, msg: String) -> None:
        """Robot arm finished executing — clear busy flag."""
        self._robot_busy = False

    def _on_user_punch(self, msg: ConfirmedPunch) -> None:
        """Track user punch timestamps for idle detection."""
        self._last_user_punch = msg.timestamp if msg.timestamp > 0 else time.time()

    def _on_imu_punch(self, msg: PunchEvent) -> None:
        """React to user pad strikes with counter-punches (sparring mode only).

        Free mode does NOT use the sparring engine — the V4 GUI's own
        handle_strike does counter-punches directly on the hardware.
        """
        if not self._active or self._mode != "sparring":
            return
        if self._robot_busy or not self._counters_enabled:
            return
        now = time.time()
        if now - self._ft_last_counter < max(self._ft_cooldown_s, 0.5):
            return

        # Probabilistic counter based on difficulty
        prob = self._counter_prob.get(self._difficulty, 0.5)
        if random.random() > prob:
            return

        pad = msg.pad
        strikes = self._ft_counter_strikes.get(pad)
        if not strikes:
            return
        punch_code = random.choice(strikes)
        # Use user-configured counter speed if set, else difficulty-based
        if self._counter_speed_override:
            speed = self._counter_speed_override
        else:
            speed = {"easy": "slow", "medium": "medium", "hard": "fast"}.get(
                self._difficulty, "medium")
        cmd = RobotCommand()
        cmd.command_type = "punch"
        cmd.punch_code = punch_code
        cmd.speed = speed
        cmd.source = "counter"
        self._robot_busy = True
        self._ft_last_counter = now
        self._pub_cmd.publish(cmd)
        # Reset scheduled attack timer to prevent double-up
        self._last_attack = now
        logger.debug("Counter-punch (%s): pad=%s -> code=%s", self._mode, pad, punch_code)

    def update_weakness_profile(self, profile: Dict[str, float]) -> None:
        """Set weakness profile (punch_name -> miss_rate) for targeting bias."""
        self._weakness = {
            PUNCH_NAMES.index(n): r for n, r in profile.items() if n in PUNCH_NAMES
        }

    def set_user_blocked(self) -> None:
        """Signal that the user blocked the last robot punch."""
        self._blocked_last = True

    def _tick(self) -> None:
        """Main loop -- decide whether to attack this tick (sparring mode only)."""
        if not self._active or self._mode != "sparring":
            return
        now = time.time()
        # Watchdog: deactivate if session_manager stopped publishing state
        if self._last_session_msg > 0 and (now - self._last_session_msg) > self._session_timeout_s:
            logger.warning("No SessionState for %.0fs — deactivating (session_manager down?)",
                           now - self._last_session_msg)
            self._active = False
            self._robot_busy = False
            return
        interval = DIFF_INTERVAL.get(self._difficulty, 1.2)
        # Style switching for 'switch' mode
        if self._style == "switch" and now - self._switch_at >= self._switch_interval:
            opts = [s for s in STYLES if s not in ("switch", self._active_style)]
            self._active_style = random.choice(opts)
            self._switch_at = now
            logger.info("Style switched to '%s'", self._active_style)
        # Surprise attack on idle user
        if (now - self._last_user_punch) > IDLE_THRESHOLD_S and (now - self._last_attack) > interval * 0.6:
            self._attack(now)
            return
        if now - self._last_attack >= interval:
            self._attack(now)

    def _attack(self, now: float) -> None:
        """Select and publish the next robot punch.

        Only one arm at a time — skip if robot is busy or counter just fired.
        """
        if self._robot_busy:
            return
        nxt = self._select()
        if self._blocked_last and nxt == self._cur_idx:
            alts = [i for i in range(len(PUNCH_CODES)) if i != nxt]
            nxt = random.choice(alts)
            self._blocked_last = False
        self._cur_idx = nxt
        self._last_attack = now
        msg = RobotCommand()
        msg.command_type = "punch"
        msg.punch_code = PUNCH_CODES[nxt]
        msg.source = "scheduled"
        msg.speed = {"easy": "slow", "medium": "medium", "hard": "fast"}.get(self._difficulty, "medium")
        self._robot_busy = True
        self._pub_cmd.publish(msg)
        logger.info("Robot attack: %s (style=%s, diff=%s)",
                    PUNCH_NAMES[nxt], self._active_style, self._difficulty)

    def _select(self) -> int:
        """Markov transition + weakness bias -> next punch index."""
        matrix = STYLES.get(self._active_style) or STYLES["boxer"]
        if not matrix:
            matrix = STYLES["boxer"]
        weights = list(matrix[self._cur_idx])
        for idx, rate in self._weakness.items():
            if 0 <= idx < len(weights):
                weights[idx] += WEAKNESS_BIAS * rate
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]
        r = random.random()
        cum = 0.0
        for idx, w in enumerate(weights):
            cum += w
            if r <= cum:
                return idx
        return len(weights) - 1


def main(args: list[str] | None = None) -> None:
    """Entry point for the sparring engine node."""
    rclpy.init(args=args)
    node = SparringEngine()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
