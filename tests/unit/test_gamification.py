"""Tests for the BoxBunny gamification engine.

Tests XP calculation, rank progression, session scoring, streak management,
and achievement unlocking -- all without hardware or ROS.
"""

import pytest


# XP calculation constants (should match the engine)
RANK_THRESHOLDS = [
    ("Novice", 0), ("Contender", 500), ("Fighter", 1500),
    ("Warrior", 4000), ("Champion", 10000), ("Elite", 25000),
]

BASE_XP = {
    "training": 50, "sparring": 75, "free": 25,
    "power": 30, "stamina": 40, "reaction": 30,
}


def _get_rank(total_xp: int) -> str:
    """Calculate rank from XP."""
    rank = "Novice"
    for name, threshold in reversed(RANK_THRESHOLDS):
        if total_xp >= threshold:
            rank = name
            break
    return rank


def _xp_to_next(total_xp: int) -> tuple:
    """Get XP needed for next rank."""
    for i, (name, threshold) in enumerate(RANK_THRESHOLDS):
        if total_xp < threshold:
            return threshold - total_xp, name
    return 0, "Elite"


def _compute_session_xp(mode: str, score: int, is_complete: bool, streak_bonus: int = 0) -> int:
    """Compute total XP for a session."""
    base = BASE_XP.get(mode, 25)
    score_multiplier = max(0.5, score / 100.0)
    completion_bonus = 1.5 if is_complete else 1.0
    total = int(base * score_multiplier * completion_bonus) + streak_bonus
    return total


# ═══════════════════════════════════════════════════════════════════════════════
# Rank System
# ═══════════════════════════════════════════════════════════════════════════════

class TestRankSystem:
    """Test rank calculations."""

    def test_novice_at_zero(self):
        assert _get_rank(0) == "Novice"

    def test_contender_at_500(self):
        assert _get_rank(500) == "Contender"

    def test_fighter_at_1500(self):
        assert _get_rank(1500) == "Fighter"

    def test_warrior_at_4000(self):
        assert _get_rank(4000) == "Warrior"

    def test_champion_at_10000(self):
        assert _get_rank(10000) == "Champion"

    def test_elite_at_25000(self):
        assert _get_rank(25000) == "Elite"

    def test_between_ranks(self):
        assert _get_rank(999) == "Contender"
        assert _get_rank(1499) == "Contender"
        assert _get_rank(3999) == "Fighter"

    def test_very_high_xp(self):
        assert _get_rank(100000) == "Elite"

    def test_xp_to_next_from_zero(self):
        remaining, next_rank = _xp_to_next(0)
        assert remaining == 500
        assert next_rank == "Contender"

    def test_xp_to_next_from_elite(self):
        remaining, next_rank = _xp_to_next(30000)
        assert remaining == 0
        assert next_rank == "Elite"

    def test_xp_to_next_just_below_threshold(self):
        remaining, next_rank = _xp_to_next(499)
        assert remaining == 1
        assert next_rank == "Contender"

    def test_rank_progression_order(self):
        """Ranks should increase monotonically with XP."""
        xp_values = [0, 100, 500, 1000, 1500, 3000, 4000, 8000, 10000, 20000, 25000]
        ranks = [_get_rank(xp) for xp in xp_values]
        rank_indices = [
            next(i for i, (name, _) in enumerate(RANK_THRESHOLDS) if name == rank)
            for rank in ranks
        ]
        for i in range(len(rank_indices) - 1):
            assert rank_indices[i] <= rank_indices[i + 1]


# ═══════════════════════════════════════════════════════════════════════════════
# XP Calculation Per Mode
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionXP:
    """Test session XP calculations per mode."""

    def test_base_xp_training(self):
        assert BASE_XP["training"] == 50

    def test_base_xp_sparring(self):
        assert BASE_XP["sparring"] == 75

    def test_base_xp_free(self):
        assert BASE_XP["free"] == 25

    def test_base_xp_power(self):
        assert BASE_XP["power"] == 30

    def test_base_xp_stamina(self):
        assert BASE_XP["stamina"] == 40

    def test_base_xp_reaction(self):
        assert BASE_XP["reaction"] == 30

    def test_sparring_yields_more_than_free(self):
        xp_sparring = _compute_session_xp("sparring", 50, True)
        xp_free = _compute_session_xp("free", 50, True)
        assert xp_sparring > xp_free

    def test_complete_session_bonus(self):
        xp_complete = _compute_session_xp("training", 80, True)
        xp_incomplete = _compute_session_xp("training", 80, False)
        assert xp_complete > xp_incomplete

    def test_high_score_yields_more_xp(self):
        xp_high = _compute_session_xp("training", 100, True)
        xp_low = _compute_session_xp("training", 20, True)
        assert xp_high > xp_low

    def test_streak_bonus_adds_xp(self):
        xp_no_streak = _compute_session_xp("training", 50, True, streak_bonus=0)
        xp_streak = _compute_session_xp("training", 50, True, streak_bonus=25)
        assert xp_streak == xp_no_streak + 25

    def test_minimum_xp_floor(self):
        """Even a terrible session should give some XP."""
        xp = _compute_session_xp("training", 0, False)
        assert xp > 0  # Floor of 0.5 multiplier ensures some XP


# ═══════════════════════════════════════════════════════════════════════════════
# Session Scoring
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionScore:
    """Test session scoring (0-100)."""

    def _compute_score(
        self,
        volume_ratio: float = 0.5,
        accuracy: float = 0.5,
        consistency: float = 0.5,
        improvement: float = 0.0,
    ) -> int:
        """Simplified session score computation."""
        score = (
            volume_ratio * 30
            + accuracy * 30
            + consistency * 25
            + improvement * 15
        )
        return max(0, min(100, int(score)))

    def test_perfect_score(self):
        score = self._compute_score(1.0, 1.0, 1.0, 1.0)
        assert score == 100

    def test_zero_score(self):
        score = self._compute_score(0.0, 0.0, 0.0, 0.0)
        assert score == 0

    def test_average_score(self):
        score = self._compute_score(0.5, 0.5, 0.5, 0.0)
        assert 30 <= score <= 50

    def test_high_accuracy_low_volume(self):
        score = self._compute_score(0.2, 0.9, 0.7, 0.0)
        assert score > 40

    def test_clamped_to_100(self):
        # Even with impossible inputs, score should not exceed 100
        score = self._compute_score(1.5, 1.5, 1.5, 1.5)
        assert score <= 100

    def test_clamped_to_0(self):
        score = self._compute_score(-1.0, -1.0, -1.0, -1.0)
        assert score >= 0

    def test_volume_weight(self):
        """Volume contributes 30% of total score."""
        score_with = self._compute_score(volume_ratio=1.0, accuracy=0.0, consistency=0.0, improvement=0.0)
        assert score_with == 30

    def test_improvement_bonus(self):
        """Improvement adds up to 15 points."""
        base = self._compute_score(0.5, 0.5, 0.5, 0.0)
        improved = self._compute_score(0.5, 0.5, 0.5, 1.0)
        assert improved - base == 15


# ═══════════════════════════════════════════════════════════════════════════════
# Rank Progression (via Database)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRankProgression:
    """Test rank progression through the database manager."""

    def test_initial_xp_is_zero(self, db_manager, sample_user):
        xp_data = db_manager.get_user_xp(sample_user["username"])
        assert xp_data["total_xp"] == 0
        assert xp_data["current_rank"] == "Novice"

    def test_add_xp_accumulates(self, db_manager, sample_user):
        db_manager.add_xp(sample_user["username"], 100)
        result = db_manager.add_xp(sample_user["username"], 200)
        assert result["total_xp"] == 300
        assert result["current_rank"] == "Novice"

    def test_rank_up_to_contender(self, db_manager, sample_user):
        result = db_manager.add_xp(sample_user["username"], 500)
        assert result["current_rank"] == "Contender"
        assert result["ranked_up"] is True

    def test_rank_up_to_fighter(self, db_manager, sample_user):
        db_manager.add_xp(sample_user["username"], 500)
        result = db_manager.add_xp(sample_user["username"], 1000)
        assert result["current_rank"] == "Fighter"
        assert result["ranked_up"] is True

    def test_no_rank_up_within_same_tier(self, db_manager, sample_user):
        db_manager.add_xp(sample_user["username"], 100)
        result = db_manager.add_xp(sample_user["username"], 100)
        assert result["ranked_up"] is False

    def test_skip_rank(self, db_manager, sample_user):
        """Adding a large amount of XP at once can skip intermediate ranks."""
        result = db_manager.add_xp(sample_user["username"], 5000)
        assert result["current_rank"] == "Warrior"


# ═══════════════════════════════════════════════════════════════════════════════
# Streak Management
# ═══════════════════════════════════════════════════════════════════════════════

class TestStreakManagement:
    """Test training streak tracking."""

    def test_first_session_starts_streak(self, db_manager, sample_user):
        streak = db_manager.update_streak(sample_user["username"])
        assert streak["current_streak"] == 1

    def test_same_day_does_not_increment(self, db_manager, sample_user):
        db_manager.update_streak(sample_user["username"])
        streak = db_manager.update_streak(sample_user["username"])
        assert streak["current_streak"] == 1

    def test_longest_streak_tracked(self, db_manager, sample_user):
        streak = db_manager.update_streak(sample_user["username"])
        assert streak["longest_streak"] >= streak["current_streak"]

    def test_weekly_progress_increments(self, db_manager, sample_user):
        streak = db_manager.update_streak(sample_user["username"])
        assert streak["weekly_progress"] >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# Achievement Unlocking
# ═══════════════════════════════════════════════════════════════════════════════

class TestAchievements:
    """Test achievement unlock system."""

    def test_unlock_new_achievement(self, db_manager, sample_user):
        result = db_manager.unlock_achievement(sample_user["username"], "first_blood")
        assert result is True

    def test_duplicate_unlock_returns_false(self, db_manager, sample_user):
        db_manager.unlock_achievement(sample_user["username"], "first_blood")
        result = db_manager.unlock_achievement(sample_user["username"], "first_blood")
        assert result is False

    def test_multiple_different_achievements(self, db_manager, sample_user):
        db_manager.unlock_achievement(sample_user["username"], "first_blood")
        db_manager.unlock_achievement(sample_user["username"], "combo_master")
        db_manager.unlock_achievement(sample_user["username"], "iron_chin")
        achievements = db_manager.get_achievements(sample_user["username"])
        assert len(achievements) == 3

    def test_achievement_ids_stored(self, db_manager, sample_user):
        db_manager.unlock_achievement(sample_user["username"], "speed_demon")
        achievements = db_manager.get_achievements(sample_user["username"])
        ids = [a["achievement_id"] for a in achievements]
        assert "speed_demon" in ids

    def test_no_achievements_initially(self, db_manager, sample_user):
        achievements = db_manager.get_achievements(sample_user["username"])
        assert len(achievements) == 0

    def test_achievement_has_timestamp(self, db_manager, sample_user):
        db_manager.unlock_achievement(sample_user["username"], "first_blood")
        achievements = db_manager.get_achievements(sample_user["username"])
        assert achievements[0]["unlocked_at"] is not None


# ═══════════════════════════════════════════════════════════════════════════════
# Personal Records
# ═══════════════════════════════════════════════════════════════════════════════

class TestPersonalRecords:
    """Test personal record tracking."""

    def test_new_record(self, db_manager, sample_user):
        pr = db_manager.check_personal_record(sample_user["username"], "max_punches", 87)
        assert pr is not None
        assert pr["is_new"] is True
        assert pr["value"] == 87

    def test_broken_record(self, db_manager, sample_user):
        db_manager.check_personal_record(sample_user["username"], "max_punches", 50)
        pr = db_manager.check_personal_record(sample_user["username"], "max_punches", 87)
        assert pr is not None
        assert pr["previous_value"] == 50.0
        assert pr["value"] == 87

    def test_not_broken(self, db_manager, sample_user):
        db_manager.check_personal_record(sample_user["username"], "max_punches", 100)
        pr = db_manager.check_personal_record(sample_user["username"], "max_punches", 87)
        assert pr is None

    def test_different_record_types(self, db_manager, sample_user):
        pr1 = db_manager.check_personal_record(sample_user["username"], "max_punches", 87)
        pr2 = db_manager.check_personal_record(sample_user["username"], "fastest_reaction_ms", 180.0)
        assert pr1 is not None
        assert pr2 is not None
