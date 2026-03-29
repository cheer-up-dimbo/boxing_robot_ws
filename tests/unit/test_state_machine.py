"""Tests for the CausalActionStateMachine from action_prediction/lib/state_machine.py.

Tests idle-to-active transitions, consecutive frame requirements, peak drop exit,
sustain confidence, and overall state machine behavior -- all without hardware.
"""

import numpy as np
import pytest

from lib.state_machine import CausalActionStateMachine


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def make_probs(labels, target_label, confidence=0.9):
    """Build a probability vector with `confidence` on `target_label` and spread the rest."""
    n = len(labels)
    idx = labels.index(target_label)
    probs = np.full(n, (1.0 - confidence) / (n - 1), dtype=np.float32)
    probs[idx] = confidence
    return probs


def make_sm(labels, **overrides):
    """Create a CausalActionStateMachine with defaults and optional overrides."""
    config = {
        "enter_consecutive": 2,
        "exit_consecutive": 2,
        "min_hold_steps": 2,
        "sustain_confidence": 0.78,
        "peak_drop_threshold": 0.02,
    }
    config.update(overrides)
    return CausalActionStateMachine(labels=labels, **config)


# ═══════════════════════════════════════════════════════════════════════════════
# Basic State Transitions
# ═══════════════════════════════════════════════════════════════════════════════

class TestIdleState:
    """Test behavior in idle state."""

    def test_starts_idle(self, action_labels):
        sm = make_sm(action_labels)
        assert sm.active_idx is None
        assert sm.active_steps == 0

    def test_idle_prediction_stays_idle(self, action_labels):
        sm = make_sm(action_labels)
        idle_idx = action_labels.index("idle")
        probs = make_probs(action_labels, "idle", 0.95)
        result = sm.update(probs, idle_idx, 0.95)
        assert result["state"] == "idle"
        assert result["pred_idx"] == idle_idx

    def test_single_non_idle_frame_stays_idle(self, action_labels):
        """One frame of a punch should not activate -- need consecutive frames."""
        sm = make_sm(action_labels, enter_consecutive=2)
        jab_idx = action_labels.index("jab")
        probs = make_probs(action_labels, "jab", 0.9)
        result = sm.update(probs, jab_idx, 0.9)
        assert result["state"] == "idle"
        assert sm.active_idx is None

    def test_idle_frame_resets_enter_candidate(self, action_labels):
        sm = make_sm(action_labels, enter_consecutive=3)
        jab_idx = action_labels.index("jab")
        idle_idx = action_labels.index("idle")

        # One jab frame
        probs_jab = make_probs(action_labels, "jab", 0.9)
        sm.update(probs_jab, jab_idx, 0.9)
        assert sm.enter_count == 1

        # Idle frame resets
        probs_idle = make_probs(action_labels, "idle", 0.95)
        sm.update(probs_idle, idle_idx, 0.95)
        assert sm.enter_count == 0
        assert sm.enter_candidate_idx is None


# ═══════════════════════════════════════════════════════════════════════════════
# Idle to Active Transitions
# ═══════════════════════════════════════════════════════════════════════════════

class TestActivation:
    """Test transition from idle to active state."""

    def test_consecutive_frames_activate(self, action_labels):
        sm = make_sm(action_labels, enter_consecutive=2)
        jab_idx = action_labels.index("jab")
        probs = make_probs(action_labels, "jab", 0.9)

        # Frame 1: candidate registered
        r1 = sm.update(probs, jab_idx, 0.9)
        assert r1["state"] == "idle"

        # Frame 2: consecutive threshold met -> activate
        r2 = sm.update(probs, jab_idx, 0.9)
        assert r2["state"] == "activated"
        assert r2["pred_idx"] == jab_idx
        assert sm.active_idx == jab_idx

    def test_enter_consecutive_3(self, action_labels):
        sm = make_sm(action_labels, enter_consecutive=3)
        cross_idx = action_labels.index("cross")
        probs = make_probs(action_labels, "cross", 0.85)

        sm.update(probs, cross_idx, 0.85)
        sm.update(probs, cross_idx, 0.85)
        r = sm.update(probs, cross_idx, 0.85)
        assert r["state"] == "activated"

    def test_different_label_resets_counter(self, action_labels):
        sm = make_sm(action_labels, enter_consecutive=3)
        jab_idx = action_labels.index("jab")
        cross_idx = action_labels.index("cross")

        probs_jab = make_probs(action_labels, "jab", 0.9)
        probs_cross = make_probs(action_labels, "cross", 0.85)

        sm.update(probs_jab, jab_idx, 0.9)
        sm.update(probs_jab, jab_idx, 0.9)

        # Switch to cross -- should reset the counter
        sm.update(probs_cross, cross_idx, 0.85)
        assert sm.enter_count == 1
        assert sm.enter_candidate_idx == cross_idx

    def test_activation_records_peak_conf(self, action_labels):
        sm = make_sm(action_labels, enter_consecutive=2)
        jab_idx = action_labels.index("jab")
        probs = make_probs(action_labels, "jab", 0.92)

        sm.update(probs, jab_idx, 0.92)
        sm.update(probs, jab_idx, 0.92)
        assert sm.active_peak_conf == pytest.approx(0.92, abs=0.01)


# ═══════════════════════════════════════════════════════════════════════════════
# Consecutive Frame Requirements
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsecutiveFrames:
    """Test that the consecutive frame requirement is enforced."""

    def test_enter_consecutive_1(self, action_labels):
        """With enter_consecutive=1, first non-idle frame should activate."""
        sm = make_sm(action_labels, enter_consecutive=1)
        jab_idx = action_labels.index("jab")
        probs = make_probs(action_labels, "jab", 0.9)
        r = sm.update(probs, jab_idx, 0.9)
        assert r["state"] == "activated"

    def test_exit_consecutive_requirement(self, action_labels):
        """Exit requires consecutive exit frames, not just one."""
        sm = make_sm(action_labels, enter_consecutive=1, exit_consecutive=3, min_hold_steps=0)
        jab_idx = action_labels.index("jab")
        idle_idx = action_labels.index("idle")

        probs_jab = make_probs(action_labels, "jab", 0.9)
        probs_idle = make_probs(action_labels, "idle", 0.95)

        # Activate
        sm.update(probs_jab, jab_idx, 0.9)
        assert sm.active_idx == jab_idx

        # First exit frame -- not enough
        r1 = sm.update(probs_idle, idle_idx, 0.95)
        assert r1["state"] == "active"  # Still active

        # Second exit frame
        r2 = sm.update(probs_idle, idle_idx, 0.95)
        assert r2["state"] == "active"

        # Third exit frame -- now exits
        r3 = sm.update(probs_idle, idle_idx, 0.95)
        assert r3["state"] == "deactivated"

    def test_exit_counter_resets_on_non_exit(self, action_labels):
        """If exit signal disappears, the exit counter resets."""
        sm = make_sm(action_labels, enter_consecutive=1, exit_consecutive=3, min_hold_steps=0)
        jab_idx = action_labels.index("jab")
        idle_idx = action_labels.index("idle")

        probs_jab = make_probs(action_labels, "jab", 0.9)
        probs_idle = make_probs(action_labels, "idle", 0.95)

        sm.update(probs_jab, jab_idx, 0.9)  # Activate

        # Two exit frames
        sm.update(probs_idle, idle_idx, 0.95)
        sm.update(probs_idle, idle_idx, 0.95)

        # Jab frame interrupts the exit
        sm.update(probs_jab, jab_idx, 0.9)
        assert sm.exit_count == 0

        # Need another 3 consecutive exit frames now
        sm.update(probs_idle, idle_idx, 0.95)
        r = sm.update(probs_idle, idle_idx, 0.95)
        assert r["state"] == "active"  # Only 2 exit frames so far


# ═══════════════════════════════════════════════════════════════════════════════
# Min Hold Steps
# ═══════════════════════════════════════════════════════════════════════════════

class TestMinHoldSteps:
    """Test the minimum hold requirement before deactivation."""

    def test_cannot_exit_before_min_hold(self, action_labels):
        sm = make_sm(action_labels, enter_consecutive=1, exit_consecutive=1, min_hold_steps=5)
        jab_idx = action_labels.index("jab")
        idle_idx = action_labels.index("idle")

        probs_jab = make_probs(action_labels, "jab", 0.9)
        probs_idle = make_probs(action_labels, "idle", 0.95)

        sm.update(probs_jab, jab_idx, 0.9)  # Activate (step 1)

        # Steps 2-4: try to exit immediately
        for _ in range(3):
            r = sm.update(probs_idle, idle_idx, 0.95)
            assert r["state"] == "active"  # Cannot exit yet

    def test_can_exit_after_min_hold(self, action_labels):
        sm = make_sm(action_labels, enter_consecutive=1, exit_consecutive=1, min_hold_steps=3)
        jab_idx = action_labels.index("jab")
        idle_idx = action_labels.index("idle")

        probs_jab = make_probs(action_labels, "jab", 0.9)
        probs_idle = make_probs(action_labels, "idle", 0.95)

        sm.update(probs_jab, jab_idx, 0.9)  # Activate (step 1)

        # Hold for min_hold_steps with the jab active
        sm.update(probs_jab, jab_idx, 0.9)  # step 2
        sm.update(probs_jab, jab_idx, 0.9)  # step 3 (min_hold met)

        # Now idle should trigger deactivation
        r = sm.update(probs_idle, idle_idx, 0.95)
        assert r["state"] == "deactivated"


# ═══════════════════════════════════════════════════════════════════════════════
# Peak Drop Exit
# ═══════════════════════════════════════════════════════════════════════════════

class TestPeakDropExit:
    """Test deactivation triggered by confidence dropping from peak."""

    def test_peak_drop_triggers_exit(self, action_labels):
        sm = make_sm(
            action_labels,
            enter_consecutive=1,
            exit_consecutive=1,
            min_hold_steps=0,
            sustain_confidence=0.0,  # Disable sustain to isolate peak drop
            peak_drop_threshold=0.1,
        )
        jab_idx = action_labels.index("jab")
        probs_high = make_probs(action_labels, "jab", 0.95)
        probs_low = make_probs(action_labels, "jab", 0.80)

        sm.update(probs_high, jab_idx, 0.95)  # Activate with high conf
        assert sm.active_peak_conf == pytest.approx(0.95, abs=0.01)

        # Confidence drops by 0.15 (> threshold of 0.1)
        r = sm.update(probs_low, jab_idx, 0.80)
        assert r["state"] == "deactivated"
        assert "peak_drop" in r.get("exit_reasons", [])

    def test_no_peak_drop_within_threshold(self, action_labels):
        sm = make_sm(
            action_labels,
            enter_consecutive=1,
            exit_consecutive=1,
            min_hold_steps=0,
            sustain_confidence=0.0,
            peak_drop_threshold=0.1,
        )
        jab_idx = action_labels.index("jab")
        probs_high = make_probs(action_labels, "jab", 0.95)
        probs_slight_drop = make_probs(action_labels, "jab", 0.90)

        sm.update(probs_high, jab_idx, 0.95)

        # Drop of 0.05 (< threshold of 0.1) -- should stay active
        r = sm.update(probs_slight_drop, jab_idx, 0.90)
        assert r["state"] == "active"

    def test_peak_tracks_highest(self, action_labels):
        sm = make_sm(action_labels, enter_consecutive=1, min_hold_steps=0)
        jab_idx = action_labels.index("jab")

        sm.update(make_probs(action_labels, "jab", 0.80), jab_idx, 0.80)
        sm.update(make_probs(action_labels, "jab", 0.92), jab_idx, 0.92)
        sm.update(make_probs(action_labels, "jab", 0.85), jab_idx, 0.85)

        assert sm.active_peak_conf == pytest.approx(0.92, abs=0.01)


# ═══════════════════════════════════════════════════════════════════════════════
# Sustain Confidence
# ═══════════════════════════════════════════════════════════════════════════════

class TestSustainConfidence:
    """Test deactivation triggered by confidence falling below sustain threshold."""

    def test_sustain_below_threshold_triggers_exit(self, action_labels):
        sm = make_sm(
            action_labels,
            enter_consecutive=1,
            exit_consecutive=1,
            min_hold_steps=0,
            sustain_confidence=0.78,
            peak_drop_threshold=0.0,  # Disable peak drop to isolate sustain
        )
        jab_idx = action_labels.index("jab")

        sm.update(make_probs(action_labels, "jab", 0.9), jab_idx, 0.9)

        # Confidence drops below sustain threshold
        r = sm.update(make_probs(action_labels, "jab", 0.5), jab_idx, 0.5)
        assert r["state"] == "deactivated"
        assert "sustain" in r.get("exit_reasons", [])

    def test_sustain_at_threshold_stays_active(self, action_labels):
        sm = make_sm(
            action_labels,
            enter_consecutive=1,
            exit_consecutive=2,  # Need 2 exit frames
            min_hold_steps=0,
            sustain_confidence=0.78,
            peak_drop_threshold=0.0,
        )
        jab_idx = action_labels.index("jab")

        sm.update(make_probs(action_labels, "jab", 0.9), jab_idx, 0.9)

        # At exactly the threshold, no sustain exit signal
        r = sm.update(make_probs(action_labels, "jab", 0.78), jab_idx, 0.78)
        assert r["state"] == "active"

    def test_sustain_disabled_at_zero(self, action_labels):
        sm = make_sm(
            action_labels,
            enter_consecutive=1,
            exit_consecutive=1,
            min_hold_steps=0,
            sustain_confidence=0.0,
            peak_drop_threshold=0.0,
        )
        jab_idx = action_labels.index("jab")

        sm.update(make_probs(action_labels, "jab", 0.9), jab_idx, 0.9)

        # Even very low confidence should not trigger sustain exit
        r = sm.update(make_probs(action_labels, "jab", 0.1), jab_idx, 0.1)
        # Without sustain and peak_drop, only idle/switch proposals trigger exit
        assert r["state"] == "active"


# ═══════════════════════════════════════════════════════════════════════════════
# Reset
# ═══════════════════════════════════════════════════════════════════════════════

class TestReset:
    """Test that reset clears all state."""

    def test_reset_clears_active(self, action_labels):
        sm = make_sm(action_labels, enter_consecutive=1)
        jab_idx = action_labels.index("jab")
        sm.update(make_probs(action_labels, "jab", 0.9), jab_idx, 0.9)
        assert sm.active_idx is not None

        sm.reset()
        assert sm.active_idx is None
        assert sm.active_steps == 0
        assert sm.active_peak_conf == 0.0
        assert sm.enter_candidate_idx is None
        assert sm.enter_count == 0
        assert sm.exit_count == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Label Without Idle
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoIdleLabel:
    """Test behavior when 'idle' is not in the label list."""

    def test_passthrough_without_idle(self):
        labels = ["jab", "cross", "hook"]
        sm = CausalActionStateMachine(
            labels=labels,
            enter_consecutive=2,
            exit_consecutive=2,
            min_hold_steps=2,
            sustain_confidence=0.78,
            peak_drop_threshold=0.02,
        )
        probs = np.array([0.8, 0.1, 0.1], dtype=np.float32)
        r = sm.update(probs, 0, 0.8)
        assert r["state"] == "passthrough"
        assert r["pred_idx"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Action Switching
# ═══════════════════════════════════════════════════════════════════════════════

class TestActionSwitching:
    """Test transitioning between different active actions."""

    def test_switch_action_deactivates_first(self, action_labels):
        sm = make_sm(
            action_labels,
            enter_consecutive=1,
            exit_consecutive=1,
            min_hold_steps=0,
            sustain_confidence=0.0,
            peak_drop_threshold=0.0,
        )
        jab_idx = action_labels.index("jab")
        cross_idx = action_labels.index("cross")

        sm.update(make_probs(action_labels, "jab", 0.9), jab_idx, 0.9)
        assert sm.active_idx == jab_idx

        # Propose cross while jab is active -- triggers switch exit
        r = sm.update(make_probs(action_labels, "cross", 0.85), cross_idx, 0.85)
        assert r["state"] == "deactivated"
        assert "switch" in r.get("exit_reasons", [])

    def test_switch_sets_new_enter_candidate(self, action_labels):
        sm = make_sm(
            action_labels,
            enter_consecutive=2,
            exit_consecutive=1,
            min_hold_steps=0,
            sustain_confidence=0.0,
            peak_drop_threshold=0.0,
        )
        jab_idx = action_labels.index("jab")
        cross_idx = action_labels.index("cross")

        # Activate jab
        sm.update(make_probs(action_labels, "jab", 0.9), jab_idx, 0.9)
        sm.update(make_probs(action_labels, "jab", 0.9), jab_idx, 0.9)
        assert sm.active_idx == jab_idx

        # Switch to cross -- deactivates and sets cross as enter candidate
        sm.update(make_probs(action_labels, "cross", 0.85), cross_idx, 0.85)
        assert sm.enter_candidate_idx == cross_idx
        assert sm.enter_count == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Exit Reasons
# ═══════════════════════════════════════════════════════════════════════════════

class TestExitReasons:
    """Test that exit reasons are correctly reported."""

    def test_idle_exit_reason(self, action_labels):
        sm = make_sm(
            action_labels,
            enter_consecutive=1,
            exit_consecutive=1,
            min_hold_steps=0,
            sustain_confidence=0.0,
            peak_drop_threshold=0.0,
        )
        jab_idx = action_labels.index("jab")
        idle_idx = action_labels.index("idle")

        sm.update(make_probs(action_labels, "jab", 0.9), jab_idx, 0.9)
        r = sm.update(make_probs(action_labels, "idle", 0.95), idle_idx, 0.95)
        assert "idle" in r["exit_reasons"]

    def test_multiple_exit_reasons(self, action_labels):
        """An exit can have multiple reasons simultaneously."""
        sm = make_sm(
            action_labels,
            enter_consecutive=1,
            exit_consecutive=1,
            min_hold_steps=0,
            sustain_confidence=0.5,
            peak_drop_threshold=0.05,
        )
        jab_idx = action_labels.index("jab")
        idle_idx = action_labels.index("idle")

        # Activate with high confidence
        sm.update(make_probs(action_labels, "jab", 0.9), jab_idx, 0.9)

        # Then propose idle with low jab confidence -- triggers idle + sustain + peak_drop
        low_probs = make_probs(action_labels, "idle", 0.9)
        r = sm.update(low_probs, idle_idx, 0.9)
        reasons = r.get("exit_reasons", [])
        assert "idle" in reasons
