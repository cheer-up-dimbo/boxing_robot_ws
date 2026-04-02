"""Robot arm controller node for BoxBunny.

Communicates with Teensy V4 via micro-ROS topics (motor_commands /
motor_feedback) instead of raw serial. Loads punch waypoint sequences
from JSON files and executes them with wait-for-arrival.
"""

import json
import logging
import math
import time
from pathlib import Path
from typing import Dict, List, Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray, String

from boxbunny_msgs.msg import HeightCommand, RobotCommand, RoundControl

from boxbunny_core.constants import Topics

logger = logging.getLogger("boxbunny.robot_node")

_ARRIVAL_TOLERANCE = 0.2  # radians
_ARRIVAL_TIMEOUT = 8.0    # seconds
_CURRENT_SAFETY_LIMIT = 3.0  # amps


class RobotNode(Node):
    """ROS 2 node for robot arm and height motor control via micro-ROS."""

    def __init__(self) -> None:
        super().__init__("robot_node")

        # Parameters
        self.declare_parameter("heartbeat_hz", 10.0)
        self.declare_parameter("punch_sequences_dir", "")
        heartbeat_hz = self.get_parameter("heartbeat_hz").value
        seq_dir = self.get_parameter("punch_sequences_dir").value

        # Load punch sequences
        self._punch_sequences: Dict[str, List[Dict]] = {}
        self._load_punch_sequences(seq_dir)

        # Motor state (updated from motor_feedback)
        self._actual_positions = [0.0, 0.0, 0.0, 0.0]
        self._actual_currents = [0.0, 0.0, 0.0, 0.0]
        self._target_positions = [0.0, 0.0, 0.0, 0.0]
        self._speeds = [50.0, 50.0, 50.0, 50.0]
        self._enabled = False
        self._round_active = False
        self._connected = False
        self._last_feedback_time = 0.0
        self._is_executing = False

        # IMU accel from motor_feedback (4 IMUs x 3 axes)
        self._imu_accel = [[0.0, 0.0, 0.0] for _ in range(4)]

        # Speed mapping
        self._speed_map = {"slow": 30.0, "medium": 50.0, "fast": 80.0}
        self._current_speed = "medium"

        # ── Publishers (to Teensy via micro-ROS) ─────────────────────────
        self._pub_motor_cmd = self.create_publisher(
            Float64MultiArray, Topics.MOTOR_COMMANDS, 10
        )
        self._pub_height_cmd = self.create_publisher(
            String, Topics.ROBOT_HEIGHT_CMD, 10
        )
        self._pub_status = self.create_publisher(
            String, Topics.ROBOT_STATUS, 10
        )
        self._pub_strike_complete = self.create_publisher(
            String, Topics.ROBOT_STRIKE_COMPLETE, 10
        )

        # ── Subscribers (from Teensy via micro-ROS) ──────────────────────
        self.create_subscription(
            Float64MultiArray, Topics.MOTOR_FEEDBACK,
            self._on_motor_feedback, 10
        )
        # Hardware-confirmed arrival from Teensy strike_status publisher
        self.create_subscription(
            String, "/robot/strike_status",
            self._on_teensy_strike_status, 10
        )
        self._teensy_arrived = False

        # ── Subscribers (from BoxBunny system) ───────────────────────────
        self.create_subscription(
            RobotCommand, Topics.ROBOT_COMMAND,
            self._on_robot_command, 10
        )
        self.create_subscription(
            HeightCommand, Topics.ROBOT_HEIGHT,
            self._on_height_command, 10
        )
        self.create_subscription(
            RoundControl, Topics.ROBOT_ROUND_CONTROL,
            self._on_round_control, 10
        )

        # Heartbeat timer (sends motor_commands at configured rate)
        if heartbeat_hz > 0:
            self.create_timer(1.0 / heartbeat_hz, self._heartbeat)

        # Status timer
        self.create_timer(2.0, self._publish_status)

        logger.info(
            "Robot node initialized (micro-ROS mode, %d sequences loaded)",
            len(self._punch_sequences),
        )

    # ── Punch sequence loading ──────────────────────────────────────────

    def _load_punch_sequences(self, seq_dir: str) -> None:
        """Load punch waypoint sequences from JSON files."""
        if not seq_dir:
            ws_root = Path(__file__).resolve().parents[3]
            seq_dir = str(ws_root / "data" / "punch_sequences")

        seq_path = Path(seq_dir)
        if not seq_path.exists():
            logger.warning("Punch sequences directory not found: %s", seq_dir)
            return

        code_map = {
            "1_Jab": "1", "2_Cross": "2", "3_Hook": "3",
            "4_R_Hook": "4", "5_L_UC": "5", "6_R_UC": "6",
            "Left_Hook": "3b", "Right_Hook": "4b",
        }

        for json_file in seq_path.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    sequence = json.load(f)
                stem = json_file.stem
                code = code_map.get(stem, stem)
                self._punch_sequences[code] = sequence
                logger.debug(
                    "Loaded punch sequence: %s -> code '%s' (%d waypoints)",
                    json_file.name, code, len(sequence),
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to load punch sequence %s: %s", json_file, e)

    # ── Motor feedback from Teensy ──────────────────────────────────────

    def _on_motor_feedback(self, msg: Float64MultiArray) -> None:
        """Process motor feedback from Teensy (positions, currents, IMU)."""
        self._last_feedback_time = time.time()
        if not self._connected:
            self._connected = True
            logger.info("Teensy connected (receiving motor_feedback)")

        if len(msg.data) >= 8:
            self._actual_positions = list(msg.data[0:4])
            self._actual_currents = list(msg.data[4:8])

        # Extract IMU accel data (indices 9-20: 4 IMUs x 3 axes)
        if len(msg.data) >= 21:
            for i in range(4):
                base = 9 + i * 3
                self._imu_accel[i] = list(msg.data[base:base + 3])

    def _on_teensy_strike_status(self, msg: String) -> None:
        """Handle hardware-confirmed arrival from Teensy."""
        try:
            data = json.loads(msg.data)
            if data.get("status") == "arrived":
                self._teensy_arrived = True
                logger.debug("Teensy confirmed arrival: %s", data)
        except (json.JSONDecodeError, TypeError):
            pass

    # ── Robot command handling ──────────────────────────────────────────

    def _on_robot_command(self, msg: RobotCommand) -> None:
        """Handle robot punch or speed commands from BoxBunny system."""
        if msg.command_type == "set_speed":
            self._current_speed = msg.speed
            speed_val = self._speed_map.get(msg.speed, 50.0)
            self._speeds = [speed_val] * 4
            logger.info("Robot speed set to %s (%.0f)", msg.speed, speed_val)

        elif msg.command_type == "punch":
            if self._is_executing:
                logger.debug("Ignoring punch command -- already executing")
                return
            code = msg.punch_code
            sequence = self._punch_sequences.get(code)
            if sequence is None:
                logger.warning("Unknown punch code: %s", code)
                return
            # Execute in current thread context (ROS timer will still heartbeat)
            self._execute_punch(code, sequence)

    def _execute_punch(self, code: str, sequence: List[Dict]) -> None:
        """Execute a punch sequence with wait-for-arrival between waypoints."""
        self._is_executing = True
        t_start = time.time()
        logger.debug("Executing punch: code=%s (%d waypoints)", code, len(sequence))

        success = True
        for i, waypoint in enumerate(sequence):
            positions = waypoint.get("pos", [0, 0, 0, 0])
            if len(positions) < 4:
                positions = positions + [0.0] * (4 - len(positions))
            speed_l = waypoint.get("spd_l", self._speeds[0])
            speed_r = waypoint.get("spd_r", self._speeds[2])
            speeds = [speed_l, speed_l, speed_r, speed_r]

            self._send_motor_command(positions, speeds, enabled=True)

            # Wait for motors to reach target position
            arrived, reason = self._wait_for_arrival(positions)
            if not arrived:
                logger.warning(
                    "Punch %s waypoint %d: %s", code, i, reason,
                )
                if reason == "SAFETY":
                    self._enabled = False
                    self._send_motor_command(
                        self._actual_positions, [0] * 4, enabled=False,
                    )
                success = False
                break

        duration_ms = int((time.time() - t_start) * 1000)
        self._is_executing = False

        # Publish strike completion feedback
        status = "completed" if success else "aborted"
        complete_msg = String()
        complete_msg.data = json.dumps({
            "punch_code": code,
            "status": status,
            "duration_ms": duration_ms,
        })
        self._pub_strike_complete.publish(complete_msg)
        logger.debug("Punch %s %s in %dms", code, status, duration_ms)

    def _wait_for_arrival(
        self,
        targets: List[float],
        timeout: float = _ARRIVAL_TIMEOUT,
        tolerance: float = _ARRIVAL_TOLERANCE,
    ) -> tuple:
        """Block until motors reach target positions.

        Uses both Jetson-side position checking AND Teensy hardware
        confirmation (strike_status). Accepts whichever fires first.

        Returns (arrived: bool, reason: str).
        """
        self._teensy_arrived = False
        t0 = time.time()
        while time.time() - t0 < timeout:
            # Safety check: overcurrent
            for i in range(4):
                if abs(self._actual_currents[i]) > _CURRENT_SAFETY_LIMIT:
                    return False, "SAFETY"

            # Check Teensy hardware confirmation
            if self._teensy_arrived:
                self._teensy_arrived = False
                return True, "TEENSY_CONFIRMED"

            # Check Jetson-side position convergence
            all_arrived = all(
                abs(self._actual_positions[i] - targets[i]) <= tolerance
                for i in range(min(4, len(targets)))
            )
            if all_arrived:
                time.sleep(0.05)  # brief settle
                return True, "ARRIVED"

            # Allow ROS callbacks to fire during the wait
            time.sleep(0.01)  # 10ms polling

        return False, "TIMEOUT"

    # ── Height command handling ──────────────────────────────────────────

    def _on_height_command(self, msg: HeightCommand) -> None:
        """Convert BoxBunny HeightCommand to Teensy string commands."""
        height_msg = String()
        if msg.action == "stop":
            height_msg.data = "STOP"
        elif msg.action == "manual_up":
            height_msg.data = "UP:200"
        elif msg.action == "manual_down":
            height_msg.data = "DOWN:200"
        elif msg.action == "adjust":
            error = msg.current_height_px - msg.target_height_px
            pwm = min(255, int(abs(error) * 2))
            direction = "UP" if error > 0 else "DOWN"
            height_msg.data = f"{direction}:{pwm}"
        elif msg.action == "calibrate":
            logger.info("Height calibration requested")
            return
        else:
            return

        self._pub_height_cmd.publish(height_msg)
        logger.debug("Height command: %s", height_msg.data)

    # ── Round control ───────────────────────────────────────────────────

    def _on_round_control(self, msg: RoundControl) -> None:
        """Handle round start/stop."""
        if msg.action == "start":
            self._round_active = True
            self._enabled = True
            logger.info("Round started -- robot arm enabled")
        elif msg.action == "stop":
            self._round_active = False
            self._enabled = False
            self._send_motor_command([0, 0, 0, 0], [0, 0, 0, 0], enabled=False)
            logger.info("Round stopped -- robot arm disabled")

    # ── Motor command publishing ────────────────────────────────────────

    def _send_motor_command(
        self, positions: List[float], speeds: List[float], enabled: bool,
    ) -> None:
        """Publish motor command to Teensy via micro-ROS."""
        mode = 1.0 if enabled else 0.0
        msg = Float64MultiArray()
        msg.data = list(positions[:4]) + list(speeds[:4]) + [mode]
        self._pub_motor_cmd.publish(msg)
        self._target_positions = list(positions[:4])

    def _heartbeat(self) -> None:
        """Send heartbeat motor command to keep Teensy watchdog alive."""
        if not self._enabled:
            return
        self._send_motor_command(
            self._target_positions, self._speeds, self._enabled,
        )

    # ── Status publishing ───────────────────────────────────────────────

    def _publish_status(self) -> None:
        """Publish robot arm status."""
        # Check connection (no feedback for >2s = disconnected)
        if self._connected and (time.time() - self._last_feedback_time) > 2.0:
            self._connected = False
            logger.warning("Teensy disconnected (no motor_feedback for >2s)")

        msg = String()
        msg.data = json.dumps({
            "status": "connected" if self._connected else "disconnected",
            "round_active": self._round_active,
            "speed": self._current_speed,
            "sequences_loaded": len(self._punch_sequences),
            "executing": self._is_executing,
            "positions": [round(p, 2) for p in self._actual_positions],
        })
        self._pub_status.publish(msg)


def main(args=None) -> None:
    """Entry point for the robot node."""
    rclpy.init(args=args)
    node = RobotNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
