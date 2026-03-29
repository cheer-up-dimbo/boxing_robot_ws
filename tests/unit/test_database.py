"""Tests for the BoxBunny database manager.

All tests use temporary databases — no persistent state.
"""

import json

import pytest


class TestUserManagement:
    """Test user CRUD operations."""

    def test_create_user(self, db_manager):
        user_id = db_manager.create_user("alice", "pass123", "Alice", "individual", "beginner")
        assert user_id is not None
        assert user_id > 0

    def test_create_duplicate_user(self, db_manager):
        db_manager.create_user("alice", "pass123", "Alice")
        duplicate = db_manager.create_user("alice", "pass456", "Alice2")
        assert duplicate is None

    def test_verify_password_correct(self, db_manager, sample_user):
        user = db_manager.verify_password("testuser", "testpass123")
        assert user is not None
        assert user["username"] == "testuser"

    def test_verify_password_wrong(self, db_manager, sample_user):
        user = db_manager.verify_password("testuser", "wrongpassword")
        assert user is None

    def test_verify_password_no_user(self, db_manager):
        user = db_manager.verify_password("nonexistent", "pass")
        assert user is None

    def test_get_user(self, db_manager, sample_user):
        user = db_manager.get_user(sample_user["id"])
        assert user is not None
        assert user["display_name"] == "Test User"

    def test_list_users(self, db_manager):
        db_manager.create_user("user1", "p1", "User One", "individual")
        db_manager.create_user("user2", "p2", "User Two", "individual")
        db_manager.create_user("coach1", "p3", "Coach One", "coach")
        all_users = db_manager.list_users()
        assert len(all_users) == 3
        coaches = db_manager.list_users(user_type="coach")
        assert len(coaches) == 1
        assert coaches[0]["display_name"] == "Coach One"


class TestPatternLock:
    """Test pattern authentication."""

    def test_set_and_verify_pattern(self, db_manager, sample_user):
        pattern = [0, 1, 2, 5, 8]
        db_manager.set_pattern(sample_user["id"], pattern)
        assert db_manager.verify_pattern(sample_user["id"], pattern) is True

    def test_wrong_pattern(self, db_manager, sample_user):
        db_manager.set_pattern(sample_user["id"], [0, 1, 2])
        assert db_manager.verify_pattern(sample_user["id"], [6, 7, 8]) is False

    def test_no_pattern_set(self, db_manager, sample_user):
        assert db_manager.verify_pattern(sample_user["id"], [0, 1, 2]) is False


class TestGuestSessions:
    """Test guest session lifecycle."""

    def test_create_guest_session(self, db_manager):
        token = db_manager.create_guest_session()
        assert token is not None
        assert len(token) > 8

    def test_claim_guest_session(self, db_manager, sample_user):
        token = db_manager.create_guest_session()
        result = db_manager.claim_guest_session(token, sample_user["id"])
        assert result is True

    def test_double_claim(self, db_manager, sample_user):
        token = db_manager.create_guest_session()
        db_manager.claim_guest_session(token, sample_user["id"])
        result = db_manager.claim_guest_session(token, sample_user["id"])
        assert result is False


class TestPresets:
    """Test preset CRUD."""

    def test_create_and_get_presets(self, db_manager, sample_user, sample_preset):
        preset_id = db_manager.create_preset(
            user_id=sample_user["id"], **sample_preset
        )
        assert preset_id > 0
        presets = db_manager.get_presets(sample_user["id"])
        assert len(presets) == 1
        assert presets[0]["name"] == "Quick Jab Drill"

    def test_update_preset(self, db_manager, sample_user, sample_preset):
        preset_id = db_manager.create_preset(user_id=sample_user["id"], **sample_preset)
        db_manager.update_preset(preset_id, name="Updated Name", is_favorite=1)
        presets = db_manager.get_presets(sample_user["id"])
        assert presets[0]["name"] == "Updated Name"
        assert presets[0]["is_favorite"] == 1

    def test_increment_use_count(self, db_manager, sample_user, sample_preset):
        preset_id = db_manager.create_preset(user_id=sample_user["id"], **sample_preset)
        db_manager.increment_preset_use(preset_id)
        db_manager.increment_preset_use(preset_id)
        presets = db_manager.get_presets(sample_user["id"])
        assert presets[0]["use_count"] == 2


class TestTrainingSessions:
    """Test session data operations."""

    def test_save_and_retrieve_session(self, db_manager, sample_user, sample_session_data):
        session_id = db_manager.save_training_session(
            sample_user["username"], sample_session_data
        )
        assert session_id is not None
        history = db_manager.get_session_history(sample_user["username"])
        assert len(history) == 1

    def test_session_detail(self, db_manager, sample_user, sample_session_data):
        db_manager.save_training_session(sample_user["username"], sample_session_data)
        detail = db_manager.get_session_detail(
            sample_user["username"], sample_session_data["session_id"]
        )
        assert detail is not None
        assert detail["mode"] == "training"

    def test_filter_by_mode(self, db_manager, sample_user):
        db_manager.save_training_session(sample_user["username"], {
            "session_id": "s1", "mode": "training", "difficulty": "beginner"
        })
        db_manager.save_training_session(sample_user["username"], {
            "session_id": "s2", "mode": "sparring", "difficulty": "medium"
        })
        training = db_manager.get_session_history(sample_user["username"], mode="training")
        assert len(training) == 1


class TestGamification:
    """Test XP, ranks, streaks, and achievements."""

    def test_add_xp(self, db_manager, sample_user):
        result = db_manager.add_xp(sample_user["username"], 100)
        assert result["total_xp"] == 100
        assert result["current_rank"] == "Novice"

    def test_rank_progression(self, db_manager, sample_user):
        db_manager.add_xp(sample_user["username"], 500)
        result = db_manager.add_xp(sample_user["username"], 100)
        assert result["current_rank"] == "Contender"
        assert result["ranked_up"] is True

    def test_personal_record_new(self, db_manager, sample_user):
        pr = db_manager.check_personal_record(sample_user["username"], "max_punches", 87)
        assert pr is not None
        assert pr["is_new"] is True

    def test_personal_record_broken(self, db_manager, sample_user):
        db_manager.check_personal_record(sample_user["username"], "max_punches", 50)
        pr = db_manager.check_personal_record(sample_user["username"], "max_punches", 87)
        assert pr is not None
        assert pr["previous_value"] == 50.0

    def test_personal_record_not_broken(self, db_manager, sample_user):
        db_manager.check_personal_record(sample_user["username"], "max_punches", 100)
        pr = db_manager.check_personal_record(sample_user["username"], "max_punches", 87)
        assert pr is None

    def test_streak_update(self, db_manager, sample_user):
        streak = db_manager.update_streak(sample_user["username"])
        assert streak["current_streak"] == 1

    def test_achievement_unlock(self, db_manager, sample_user):
        assert db_manager.unlock_achievement(sample_user["username"], "first_blood") is True
        assert db_manager.unlock_achievement(sample_user["username"], "first_blood") is False
        achievements = db_manager.get_achievements(sample_user["username"])
        assert len(achievements) == 1
