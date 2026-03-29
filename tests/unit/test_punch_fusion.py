"""Tests for punch fusion logic.

Tests the CV+IMU fusion, pad-location constraints, reclassification,
ring buffer expiry, and defense classification -- all without hardware.
"""

import time

import pytest

from boxbunny_core.punch_fusion import (
    DefenseWindow,
    PendingCV,
    PendingIMU,
    RingBuffer,
    SessionStats,
    classify_defense,
    reclassify_punch,
)
from boxbunny_core.constants import DefenseType, PadLocation, PunchType


# ═══════════════════════════════════════════════════════════════════════════════
# Ring Buffer
# ═══════════════════════════════════════════════════════════════════════════════

class TestRingBuffer:
    """Test the timestamp-based ring buffer."""

    def test_append_and_len(self):
        buf = RingBuffer(maxlen=10)
        assert len(buf) == 0
        buf.append(PendingCV(timestamp=1.0, punch_type="jab", confidence=0.9))
        assert len(buf) == 1

    def test_maxlen_eviction(self):
        buf = RingBuffer(maxlen=3)
        for i in range(5):
            buf.append(PendingCV(timestamp=float(i), punch_type="jab", confidence=0.9))
        assert len(buf) == 3

    def test_expire_removes_old_items(self):
        buf = RingBuffer(maxlen=10)
        buf.append(PendingCV(timestamp=1.0, punch_type="jab", confidence=0.9))
        buf.append(PendingCV(timestamp=2.0, punch_type="cross", confidence=0.8))
        buf.append(PendingCV(timestamp=3.0, punch_type="left_hook", confidence=0.7))
        expired = buf.expire(2.0)
        assert len(expired) == 2
        assert expired[0].punch_type == "jab"
        assert expired[1].punch_type == "cross"
        assert len(buf) == 1

    def test_expire_empty_buffer(self):
        buf = RingBuffer(maxlen=10)
        expired = buf.expire(100.0)
        assert expired == []

    def test_pop_match_within_window(self):
        buf = RingBuffer(maxlen=10)
        buf.append(PendingIMU(timestamp=1.0, pad="centre", level="medium", force_normalized=0.66))
        buf.append(PendingIMU(timestamp=2.0, pad="left", level="hard", force_normalized=1.0))
        buf.append(PendingIMU(timestamp=3.0, pad="right", level="light", force_normalized=0.33))
        match = buf.pop_match(1.5, 2.5)
        assert match is not None
        assert match.pad == "left"
        assert len(buf) == 2

    def test_pop_match_no_match(self):
        buf = RingBuffer(maxlen=10)
        buf.append(PendingIMU(timestamp=1.0, pad="centre", level="medium", force_normalized=0.66))
        match = buf.pop_match(5.0, 6.0)
        assert match is None
        assert len(buf) == 1

    def test_pop_match_returns_first_in_range(self):
        buf = RingBuffer(maxlen=10)
        buf.append(PendingIMU(timestamp=1.0, pad="centre", level="light", force_normalized=0.33))
        buf.append(PendingIMU(timestamp=1.1, pad="left", level="medium", force_normalized=0.66))
        buf.append(PendingIMU(timestamp=1.2, pad="right", level="hard", force_normalized=1.0))
        match = buf.pop_match(0.9, 1.3)
        assert match.pad == "centre"
        assert len(buf) == 2

    def test_clear(self):
        buf = RingBuffer(maxlen=10)
        for i in range(5):
            buf.append(PendingCV(timestamp=float(i), punch_type="jab", confidence=0.9))
        buf.clear()
        assert len(buf) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# CV + IMU Match Within Window
# ═══════════════════════════════════════════════════════════════════════════════

class TestCVIMUFusion:
    """Test that CV and IMU events are correctly matched within a time window."""

    def test_cv_imu_match_within_window(self):
        """CV and IMU events within 200ms should match."""
        cv_buf = RingBuffer(maxlen=50)
        imu_buf = RingBuffer(maxlen=50)
        base_ts = time.time()

        cv_buf.append(PendingCV(timestamp=base_ts, punch_type="jab", confidence=0.88))
        imu_buf.append(PendingIMU(timestamp=base_ts + 0.05, pad="centre", level="medium", force_normalized=0.66))

        window_ms = 200
        window_s = window_ms / 1000.0

        # Try to find an IMU match for the CV event
        cv_event = PendingCV(timestamp=base_ts, punch_type="jab", confidence=0.88)
        imu_match = imu_buf.pop_match(cv_event.timestamp - window_s, cv_event.timestamp + window_s)
        assert imu_match is not None
        assert imu_match.pad == "centre"

    def test_cv_imu_no_match_outside_window(self):
        """CV and IMU events more than 200ms apart should not match."""
        imu_buf = RingBuffer(maxlen=50)
        base_ts = time.time()

        imu_buf.append(PendingIMU(timestamp=base_ts + 0.5, pad="centre", level="medium", force_normalized=0.66))

        window_s = 0.2
        cv_event = PendingCV(timestamp=base_ts, punch_type="jab", confidence=0.88)
        imu_match = imu_buf.pop_match(cv_event.timestamp - window_s, cv_event.timestamp + window_s)
        assert imu_match is None

    def test_multiple_matches_returns_closest(self):
        """When multiple IMU events are in window, pop_match returns the first one."""
        imu_buf = RingBuffer(maxlen=50)
        base_ts = time.time()

        imu_buf.append(PendingIMU(timestamp=base_ts + 0.02, pad="centre", level="light", force_normalized=0.33))
        imu_buf.append(PendingIMU(timestamp=base_ts + 0.15, pad="left", level="hard", force_normalized=1.0))

        window_s = 0.2
        cv_event = PendingCV(timestamp=base_ts, punch_type="jab", confidence=0.88)
        imu_match = imu_buf.pop_match(cv_event.timestamp - window_s, cv_event.timestamp + window_s)
        assert imu_match is not None
        assert imu_match.pad == "centre"  # First in the buffer within range


# ═══════════════════════════════════════════════════════════════════════════════
# Pad-Location Constraints
# ═══════════════════════════════════════════════════════════════════════════════

class TestPadConstraints:
    """Test that pad location validates punch types correctly."""

    def test_jab_valid_on_centre(self):
        assert PunchType.JAB in PadLocation.VALID_PUNCHES["centre"]

    def test_jab_valid_on_left(self):
        assert PunchType.JAB in PadLocation.VALID_PUNCHES["left"]

    def test_jab_valid_on_right(self):
        assert PunchType.JAB in PadLocation.VALID_PUNCHES["right"]

    def test_left_hook_valid_on_left(self):
        assert PunchType.LEFT_HOOK in PadLocation.VALID_PUNCHES["left"]

    def test_left_hook_invalid_on_right(self):
        assert PunchType.LEFT_HOOK not in PadLocation.VALID_PUNCHES["right"]

    def test_right_hook_valid_on_right(self):
        assert PunchType.RIGHT_HOOK in PadLocation.VALID_PUNCHES["right"]

    def test_right_hook_invalid_on_left(self):
        assert PunchType.RIGHT_HOOK not in PadLocation.VALID_PUNCHES["left"]

    def test_all_offensive_valid_on_head(self):
        for punch in PunchType.OFFENSIVE:
            assert punch in PadLocation.VALID_PUNCHES["head"]

    def test_left_uppercut_valid_on_centre(self):
        assert PunchType.LEFT_UPPERCUT in PadLocation.VALID_PUNCHES["centre"]

    def test_right_uppercut_valid_on_centre(self):
        assert PunchType.RIGHT_UPPERCUT in PadLocation.VALID_PUNCHES["centre"]


# ═══════════════════════════════════════════════════════════════════════════════
# Reclassification Logic
# ═══════════════════════════════════════════════════════════════════════════════

class TestReclassification:
    """Test the pad-constraint reclassification logic."""

    def test_valid_punch_passes_through(self):
        result = reclassify_punch("centre", "jab")
        assert result == "jab"

    def test_invalid_punch_reclassified_via_secondary(self):
        # Right hook on left pad is invalid; secondary offers jab which IS valid
        secondary = [("jab", 0.6), ("cross", 0.3)]
        result = reclassify_punch("left", "right_hook", secondary_classes=secondary)
        assert result == "jab"

    def test_invalid_punch_no_valid_secondary(self):
        # Right hook on left pad, and secondary only has right_uppercut (also invalid on left)
        secondary = [("right_uppercut", 0.5)]
        result = reclassify_punch("left", "right_hook", secondary_classes=secondary)
        assert result == "unclassified"

    def test_invalid_punch_no_secondary(self):
        result = reclassify_punch("left", "right_hook")
        assert result == "unclassified"

    def test_secondary_below_min_confidence(self):
        secondary = [("jab", 0.1)]  # Below 0.25 threshold
        result = reclassify_punch("left", "right_hook", secondary_classes=secondary, min_conf=0.25)
        assert result == "unclassified"

    def test_secondary_at_min_confidence(self):
        secondary = [("jab", 0.25)]
        result = reclassify_punch("left", "right_hook", secondary_classes=secondary, min_conf=0.25)
        assert result == "jab"

    def test_unknown_pad_passes_through(self):
        # Unknown pad should pass through without constraint
        result = reclassify_punch("unknown_pad", "right_hook")
        assert result == "right_hook"

    def test_cross_valid_on_all_standard_pads(self):
        for pad in ["left", "centre", "right"]:
            result = reclassify_punch(pad, "cross")
            assert result == "cross"


# ═══════════════════════════════════════════════════════════════════════════════
# Expired Events
# ═══════════════════════════════════════════════════════════════════════════════

class TestExpiredEvents:
    """Test that old events are properly expired from buffers."""

    def test_cv_events_expire(self):
        buf = RingBuffer(maxlen=50)
        buf.append(PendingCV(timestamp=1.0, punch_type="jab", confidence=0.9))
        buf.append(PendingCV(timestamp=2.0, punch_type="cross", confidence=0.8))
        buf.append(PendingCV(timestamp=5.0, punch_type="left_hook", confidence=0.7))

        # Expire everything at or before timestamp 3.0
        expired = buf.expire(3.0)
        assert len(expired) == 2
        assert len(buf) == 1
        assert expired[0].punch_type == "jab"
        assert expired[1].punch_type == "cross"

    def test_imu_events_expire(self):
        buf = RingBuffer(maxlen=50)
        buf.append(PendingIMU(timestamp=10.0, pad="centre", level="hard", force_normalized=1.0))
        buf.append(PendingIMU(timestamp=10.5, pad="left", level="medium", force_normalized=0.66))
        buf.append(PendingIMU(timestamp=11.0, pad="right", level="light", force_normalized=0.33))

        # Expire only the first
        expired = buf.expire(10.0)
        assert len(expired) == 1
        assert len(buf) == 2

    def test_expire_all(self):
        buf = RingBuffer(maxlen=50)
        for i in range(5):
            buf.append(PendingCV(timestamp=float(i), punch_type="jab", confidence=0.9))
        expired = buf.expire(100.0)
        assert len(expired) == 5
        assert len(buf) == 0

    def test_expire_none(self):
        buf = RingBuffer(maxlen=50)
        buf.append(PendingCV(timestamp=100.0, punch_type="jab", confidence=0.9))
        expired = buf.expire(1.0)
        assert len(expired) == 0
        assert len(buf) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Defense Detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestDefenseClassification:
    """Test the classify_defense function."""

    def test_no_arm_events_returns_unknown(self):
        struck, dtype = classify_defense(
            arm_events=[], cv_blocks=[], tracking_snapshots=[],
        )
        assert struck is False
        assert dtype == DefenseType.UNKNOWN

    def test_contact_detected_returns_hit(self):
        arm_events = [{"contact": True, "timestamp": 1.0}]
        struck, dtype = classify_defense(
            arm_events=arm_events, cv_blocks=[], tracking_snapshots=[],
        )
        assert struck is True
        assert dtype == DefenseType.HIT

    def test_block_detected_by_cv(self):
        arm_events = [{"contact": False, "timestamp": 1.0}]
        cv_blocks = [{"confidence": 0.85, "timestamp": 1.1}]
        struck, dtype = classify_defense(
            arm_events=arm_events, cv_blocks=cv_blocks, tracking_snapshots=[],
        )
        assert struck is False
        assert dtype == DefenseType.BLOCK

    def test_block_below_confidence_threshold(self):
        arm_events = [{"contact": False, "timestamp": 1.0}]
        cv_blocks = [{"confidence": 0.1, "timestamp": 1.1}]
        struck, dtype = classify_defense(
            arm_events=arm_events, cv_blocks=cv_blocks, tracking_snapshots=[],
        )
        assert struck is False
        assert dtype != DefenseType.BLOCK  # Not enough confidence for block

    def test_slip_detected_by_lateral_displacement(self):
        arm_events = [{"contact": False, "timestamp": 1.0}]
        tracking = [{"lateral_displacement": 50.0, "depth_displacement": 0.01, "timestamp": 1.05}]
        struck, dtype = classify_defense(
            arm_events=arm_events, cv_blocks=[], tracking_snapshots=tracking,
        )
        assert struck is False
        assert dtype == DefenseType.SLIP

    def test_slip_detected_by_depth_displacement(self):
        arm_events = [{"contact": False, "timestamp": 1.0}]
        tracking = [{"lateral_displacement": 5.0, "depth_displacement": 0.20, "timestamp": 1.05}]
        struck, dtype = classify_defense(
            arm_events=arm_events, cv_blocks=[], tracking_snapshots=tracking,
        )
        assert struck is False
        assert dtype == DefenseType.SLIP

    def test_dodge_detected_moderate_displacement(self):
        arm_events = [{"contact": False, "timestamp": 1.0}]
        tracking = [{"lateral_displacement": 25.0, "depth_displacement": 0.05, "timestamp": 1.05}]
        struck, dtype = classify_defense(
            arm_events=arm_events, cv_blocks=[], tracking_snapshots=tracking,
        )
        assert struck is False
        assert dtype == DefenseType.DODGE

    def test_no_defense_detected(self):
        arm_events = [{"contact": False, "timestamp": 1.0}]
        tracking = [{"lateral_displacement": 2.0, "depth_displacement": 0.01, "timestamp": 1.05}]
        struck, dtype = classify_defense(
            arm_events=arm_events, cv_blocks=[], tracking_snapshots=tracking,
        )
        assert struck is False
        assert dtype == DefenseType.UNKNOWN

    def test_block_takes_priority_over_slip(self):
        """If CV detects a block AND there's slip-level displacement, block wins."""
        arm_events = [{"contact": False, "timestamp": 1.0}]
        cv_blocks = [{"confidence": 0.8, "timestamp": 1.1}]
        tracking = [{"lateral_displacement": 60.0, "depth_displacement": 0.3, "timestamp": 1.05}]
        struck, dtype = classify_defense(
            arm_events=arm_events, cv_blocks=cv_blocks, tracking_snapshots=tracking,
        )
        assert struck is False
        assert dtype == DefenseType.BLOCK  # Block checked before slip

    def test_contact_takes_priority_over_block(self):
        """If contact is detected, it's a hit regardless of block detection."""
        arm_events = [{"contact": True, "timestamp": 1.0}]
        cv_blocks = [{"confidence": 0.95, "timestamp": 1.1}]
        struck, dtype = classify_defense(
            arm_events=arm_events, cv_blocks=cv_blocks, tracking_snapshots=[],
        )
        assert struck is True
        assert dtype == DefenseType.HIT


# ═══════════════════════════════════════════════════════════════════════════════
# Session Stats
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionStats:
    """Test the running session statistics accumulator."""

    def test_record_punch(self):
        stats = SessionStats()
        stats.record_punch("jab", "centre", 0.66, "medium", 0.88, True)
        assert stats.total_punches == 1
        assert stats.punch_counts["jab"] == 1
        assert stats.imu_confirmed_count == 1

    def test_record_multiple_punches(self):
        stats = SessionStats()
        stats.record_punch("jab", "centre", 0.66, "medium", 0.88, True)
        stats.record_punch("cross", "centre", 1.0, "hard", 0.92, True)
        stats.record_punch("jab", "left", 0.33, "light", 0.80, False)
        assert stats.total_punches == 3
        assert stats.punch_counts["jab"] == 2
        assert stats.punch_counts["cross"] == 1
        assert stats.imu_confirmed_count == 2

    def test_peak_force_tracking(self):
        stats = SessionStats()
        stats.record_punch("jab", "centre", 0.5, "medium", 0.88, True)
        stats.record_punch("cross", "centre", 1.0, "hard", 0.92, True)
        stats.record_punch("jab", "centre", 0.3, "light", 0.80, True)
        assert stats.peak_force_value == 1.0
        assert stats.peak_force_level == "hard"

    def test_record_defense(self):
        stats = SessionStats()
        stats.record_defense(DefenseType.BLOCK)
        stats.record_defense(DefenseType.SLIP)
        stats.record_defense(DefenseType.HIT)
        assert stats.robot_punches_thrown == 3
        assert stats.robot_punches_landed == 1
        assert stats.defense_types[DefenseType.BLOCK] == 1
        assert stats.defense_types[DefenseType.SLIP] == 1

    def test_to_summary_fields(self):
        stats = SessionStats()
        stats.record_punch("jab", "centre", 0.66, "medium", 0.88, True)
        stats.record_punch("cross", "centre", 1.0, "hard", 0.92, True)
        summary = stats.to_summary_fields()
        assert summary["total_punches"] == 2
        assert summary["average_confidence"] == pytest.approx(0.9, abs=0.01)
        assert summary["imu_confirmation_rate"] == 1.0
