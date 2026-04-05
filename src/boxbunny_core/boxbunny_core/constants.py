"""Central constants for BoxBunny boxing training robot.

ROS topic names are loaded from ``config/ros_topics.yaml`` so you can change
any topic or service name in ONE place (the YAML file) without editing Python.

All other constants (punch types, pad locations, etc.) are defined here.
"""

import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger("boxbunny.constants")

# ── Load topic names from YAML ──────────────────────────────────────────────

_WS_ROOT = Path(__file__).resolve().parents[3]
_TOPICS_FILE = _WS_ROOT / "config" / "ros_topics.yaml"

_topic_cfg: dict = {}
try:
    with open(_TOPICS_FILE, "r") as _f:
        _topic_cfg = yaml.safe_load(_f) or {}
    logger.debug("Loaded topic names from %s", _TOPICS_FILE)
except FileNotFoundError:
    logger.warning("ros_topics.yaml not found at %s — using built-in defaults", _TOPICS_FILE)
except Exception as _e:
    logger.warning("Failed to load ros_topics.yaml: %s — using defaults", _e)


def _t(section: str, key: str, default: str) -> str:
    """Resolve a topic name from config, falling back to a built-in default."""
    return _topic_cfg.get(section, {}).get(key, default)


def _s(key: str, default: str) -> str:
    """Resolve a service name from config."""
    return _topic_cfg.get("services", {}).get(key, default)


class Topics:
    """ROS 2 topic names.

    Names are loaded from ``config/ros_topics.yaml``. If the file is missing
    or a key is absent, the hard-coded default (second arg to ``_t``) is used.
    Edit the YAML to rename any topic — no Python changes needed.
    """

    # ── IMU (from Teensy) ────────────────────────────────────────────────
    IMU_PAD_IMPACT = _t("imu", "pad_impact", "/boxbunny/imu/pad/impact")
    IMU_ARM_STRIKE = _t("imu", "arm_strike", "/boxbunny/imu/arm/strike")
    IMU_STATUS = _t("imu", "status", "/boxbunny/imu/status")

    # ── IMU (processed by imu_node) ──────────────────────────────────────
    IMU_PUNCH_EVENT = _t("imu", "punch_event", "/boxbunny/imu/punch_event")
    IMU_NAV_EVENT = _t("imu", "nav_event", "/boxbunny/imu/nav_event")
    IMU_ARM_EVENT = _t("imu", "arm_event", "/boxbunny/imu/arm_event")

    # ── CV (from cv_node) ────────────────────────────────────────────────
    CV_DETECTION = _t("cv", "detection", "/boxbunny/cv/detection")
    CV_POSE = _t("cv", "pose", "/boxbunny/cv/pose")
    CV_USER_TRACKING = _t("cv", "user_tracking", "/boxbunny/cv/user_tracking")
    CV_STATUS = _t("cv", "status", "/boxbunny/cv/status")
    CV_PERSON_DIRECTION = _t("cv", "person_direction", "/boxbunny/cv/person_direction")

    # ── Fused (from punch_processor) ─────────────────────────────────────
    PUNCH_CONFIRMED = _t("punch", "confirmed", "/boxbunny/punch/confirmed")
    PUNCH_DEFENSE = _t("punch", "defense", "/boxbunny/punch/defense")
    PUNCH_SESSION_SUMMARY = _t("punch", "session_summary", "/boxbunny/punch/session_summary")

    # ── CV debug ──────────────────────────────────────────────────────────
    CV_DEBUG_INFO = _t("cv", "debug_info", "/boxbunny/cv/debug_info")

    # ── Robot arm ────────────────────────────────────────────────────────
    ROBOT_COMMAND = _t("robot", "command", "/boxbunny/robot/command")
    ROBOT_HEIGHT = _t("robot", "height", "/boxbunny/robot/height")
    ROBOT_ROUND_CONTROL = _t("robot", "round_control", "/boxbunny/robot/round_control")
    ROBOT_STATUS = _t("robot", "status", "/boxbunny/robot/status")

    # ── Robot hardware (micro-ROS Teensy topics) ─────────────────────────
    MOTOR_COMMANDS = _t("robot", "motor_commands", "motor_commands")
    MOTOR_FEEDBACK = _t("robot", "motor_feedback", "motor_feedback")
    ROBOT_HEIGHT_CMD = _t("robot", "height_cmd", "/robot/height_cmd")
    ROBOT_STRIKE_DETECTED = _t("robot", "strike_detected", "/robot/strike_detected")
    ROBOT_STRIKE_COMPLETE = _t("robot", "strike_complete", "/boxbunny/robot/strike_complete")
    ROBOT_YAW_CMD = _t("robot", "yaw_cmd", "/robot/yaw_cmd")
    ROBOT_STRIKE_COMMAND = _t("robot", "strike_command", "/robot/strike_command")
    ROBOT_STRIKE_FEEDBACK = _t("robot", "strike_feedback", "/robot/strike_feedback")
    ROBOT_SYSTEM_ENABLE = _t("robot", "system_enable", "/robot/system_enable")

    # ── Session ──────────────────────────────────────────────────────────
    SESSION_STATE = _t("session", "state", "/boxbunny/session/state")
    SESSION_CONFIG = _t("session", "config", "/boxbunny/session/config")
    SESSION_CONFIG_JSON = _t("session", "config_json", "/boxbunny/session/config_json")

    # ── Drills ───────────────────────────────────────────────────────────
    DRILL_DEFINITION = _t("drill", "definition", "/boxbunny/drill/definition")
    DRILL_EVENT = _t("drill", "event", "/boxbunny/drill/event")
    DRILL_PROGRESS = _t("drill", "progress", "/boxbunny/drill/progress")

    # ── AI Coach ─────────────────────────────────────────────────────────
    COACH_TIP = _t("coach", "tip", "/boxbunny/coach/tip")

    # ── Analytics ────────────────────────────────────────────────────────
    ANALYTICS_SESSION = _t("analytics", "session", "/boxbunny/analytics/session")

    # ── Gesture ──────────────────────────────────────────────────────────
    GESTURE_STATUS = _t("gesture", "status", "/boxbunny/gesture/status")

    # ── Camera (RealSense) ───────────────────────────────────────────────
    CAMERA_COLOR = _t("camera", "color", "/camera/color/image_raw")
    CAMERA_DEPTH = _t("camera", "depth", "/camera/aligned_depth_to_color/image_raw")


class Services:
    """ROS 2 service names — loaded from config/ros_topics.yaml."""

    START_SESSION = _s("start_session", "/boxbunny/session/start")
    END_SESSION = _s("end_session", "/boxbunny/session/end")
    START_DRILL = _s("start_drill", "/boxbunny/drill/start")
    SET_IMU_MODE = _s("set_imu_mode", "/boxbunny/imu/set_mode")
    CALIBRATE_IMU = _s("calibrate_imu", "/boxbunny/imu/calibrate")
    GENERATE_LLM = _s("generate_llm", "/boxbunny/llm/generate")


class PunchType:
    """Punch type identifiers matching CV model output."""

    JAB = "jab"
    CROSS = "cross"
    LEFT_HOOK = "left_hook"
    RIGHT_HOOK = "right_hook"
    LEFT_UPPERCUT = "left_uppercut"
    RIGHT_UPPERCUT = "right_uppercut"
    BLOCK = "block"
    IDLE = "idle"

    ALL_ACTIONS = [
        JAB, CROSS, LEFT_HOOK, RIGHT_HOOK,
        LEFT_UPPERCUT, RIGHT_UPPERCUT, BLOCK, IDLE,
    ]
    OFFENSIVE = [
        JAB, CROSS, LEFT_HOOK, RIGHT_HOOK,
        LEFT_UPPERCUT, RIGHT_UPPERCUT,
    ]

    # Punch codes for robot commands (1-indexed)
    CODE_MAP = {
        "1": JAB,
        "2": CROSS,
        "3": LEFT_HOOK,
        "4": RIGHT_HOOK,
        "5": LEFT_UPPERCUT,
        "6": RIGHT_UPPERCUT,
    }


class PadLocation:
    """Pad IMU locations."""

    LEFT = "left"
    CENTRE = "centre"
    RIGHT = "right"
    HEAD = "head"
    ALL = [LEFT, CENTRE, RIGHT, HEAD]

    # Valid punch types per pad (for fusion constraints)
    # Centre: only jab/cross (straight punches)
    # Left: left hook or left uppercut
    # Right: right hook or right uppercut
    # Head: any offensive punch
    VALID_PUNCHES = {
        LEFT: [PunchType.LEFT_HOOK, PunchType.LEFT_UPPERCUT],
        CENTRE: [PunchType.JAB, PunchType.CROSS],
        RIGHT: [PunchType.RIGHT_HOOK, PunchType.RIGHT_UPPERCUT],
        HEAD: PunchType.OFFENSIVE,  # all offensive punches valid on head pad
    }


class ImpactLevel:
    """Impact force levels from Teensy classification."""

    LIGHT = "light"
    MEDIUM = "medium"
    HARD = "hard"
    ALL = [LIGHT, MEDIUM, HARD]
    FORCE_MAP = {LIGHT: 0.33, MEDIUM: 0.66, HARD: 1.0}


class ArmSide:
    """Robot arm sides."""

    LEFT = "left"
    RIGHT = "right"


class SessionState:
    """Session state values."""

    IDLE = "idle"
    COUNTDOWN = "countdown"
    ACTIVE = "active"
    REST = "rest"
    COMPLETE = "complete"


class TrainingMode:
    """Training mode identifiers."""

    TRAINING = "training"
    SPARRING = "sparring"
    FREE = "free"
    POWER = "power"
    STAMINA = "stamina"
    REACTION = "reaction"
    ALL = [TRAINING, SPARRING, FREE, POWER, STAMINA, REACTION]


class Difficulty:
    """Difficulty levels."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ALL = [BEGINNER, INTERMEDIATE, ADVANCED]


class Speed:
    """Robot speed settings."""

    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"


class MotorSpeed:
    """Motor speed presets (rad/s). Capped at 30 for gear safety."""

    SLOW = 8.0
    MEDIUM = 15.0
    FAST = 25.0
    MAX = 30.0

    PRESET_MAP = {"slow": SLOW, "medium": MEDIUM, "fast": FAST}


class DefenseType:
    """Defense event types."""

    BLOCK = "block"
    SLIP = "slip"
    DODGE = "dodge"
    HIT = "hit"
    UNKNOWN = "unknown"


class NavCommand:
    """IMU navigation commands."""

    PREV = "prev"
    NEXT = "next"
    ENTER = "enter"
    BACK = "back"

    # Pad-to-command mapping
    PAD_MAP = {
        PadLocation.LEFT: PREV,
        PadLocation.RIGHT: NEXT,
        PadLocation.CENTRE: ENTER,
        PadLocation.HEAD: BACK,
    }
