"""Tests for the BoxBunny database manager.

All tests use temporary databases -- no persistent state, no hardware.
"""

import json

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# User Management
# ═══════════════════════════════════════════════════════════════════════════════

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

    def test_get_user_nonexistent(self, db_manager):
        user = db_manager.get_user(99999)
        assert user is None

    def test_get_user_by_username(self, db_manager, sample_user):
        user = db_manager.get_user_by_username("testuser")
        assert user is not None
        assert user["id"] == sample_user["id"]

    def test_get_user_by_username_nonexistent(self, db_manager):
        user = db_manager.get_user_by_username("nobody")
        assert user is None

    def test_list_users(self, db_manager):
        db_manager.create_user("user1", "p1", "User One", "individual")
        db_manager.create_user("user2", "p2", "User Two", "individual")
        db_manager.create_user("coach1", "p3", "Coach One", "coach")
        all_users = db_manager.list_users()
        assert len(all_users) == 3
        coaches = db_manager.list_users(user_type="coach")
        assert len(coaches) == 1
        assert coaches[0]["display_name"] == "Coach One"

    def test_list_users_empty(self, db_manager):
        users = db_manager.list_users()
        assert users == []

    def test_user_has_correct_fields(self, db_manager, sample_user):
        user = db_manager.get_user(sample_user["id"])
        assert "username" in user
        assert "display_name" in user
        assert "user_type" in user
        assert "level" in user
        assert "created_at" in user

    def test_create_coach_user(self, db_manager):
        user_id = db_manager.create_user("coach1", "pass", "Coach", "coach", "advanced")
        user = db_manager.get_user(user_id)
        assert user["user_type"] == "coach"
        assert user["level"] == "advanced"


# ═══════════════════════════════════════════════════════════════════════════════
# Pattern Lock
# ═══════════════════════════════════════════════════════════════════════════════

class TestPatternLock:
    """Test pattern hash and verify."""

    def test_set_and_verify_pattern(self, db_manager, sample_user):
        pattern = [0, 1, 2, 5, 8]
        db_manager.set_pattern(sample_user["id"], pattern)
        assert db_manager.verify_pattern(sample_user["id"], pattern) is True

    def test_wrong_pattern(self, db_manager, sample_user):
        db_manager.set_pattern(sample_user["id"], [0, 1, 2])
        assert db_manager.verify_pattern(sample_user["id"], [6, 7, 8]) is False

    def test_no_pattern_set(self, db_manager, sample_user):
        assert db_manager.verify_pattern(sample_user["id"], [0, 1, 2]) is False

    def test_pattern_is_hashed(self, db_manager, sample_user):
        """Pattern should be stored as a bcrypt hash, not plaintext."""
        pattern = [0, 1, 2, 5, 8]
        db_manager.set_pattern(sample_user["id"], pattern)
        user = db_manager.get_user(sample_user["id"])
        # The stored hash should not be the plain pattern string
        plain = "-".join(str(s) for s in pattern)
        assert user["pattern_hash"] != plain
        assert user["pattern_hash"].startswith("$2")  # bcrypt prefix

    def test_verify_pattern_nonexistent_user(self, db_manager):
        assert db_manager.verify_pattern(99999, [0, 1, 2]) is False

    def test_overwrite_pattern(self, db_manager, sample_user):
        db_manager.set_pattern(sample_user["id"], [0, 1, 2])
        db_manager.set_pattern(sample_user["id"], [6, 7, 8])
        assert db_manager.verify_pattern(sample_user["id"], [6, 7, 8]) is True
        assert db_manager.verify_pattern(sample_user["id"], [0, 1, 2]) is False


# ═══════════════════════════════════════════════════════════════════════════════
# Guest Sessions
# ═══════════════════════════════════════════════════════════════════════════════

class TestGuestSessions:
    """Test guest session lifecycle."""

    def test_create_guest_session(self, db_manager):
        token = db_manager.create_guest_session()
        assert token is not None
        assert len(token) > 8

    def test_create_multiple_guest_sessions(self, db_manager):
        token1 = db_manager.create_guest_session()
        token2 = db_manager.create_guest_session()
        assert token1 != token2

    def test_claim_guest_session(self, db_manager, sample_user):
        token = db_manager.create_guest_session()
        result = db_manager.claim_guest_session(token, sample_user["id"])
        assert result is True

    def test_double_claim(self, db_manager, sample_user):
        token = db_manager.create_guest_session()
        db_manager.claim_guest_session(token, sample_user["id"])
        result = db_manager.claim_guest_session(token, sample_user["id"])
        assert result is False

    def test_claim_nonexistent_token(self, db_manager, sample_user):
        result = db_manager.claim_guest_session("fake_token_xyz", sample_user["id"])
        assert result is False

    def test_cleanup_expired_guests(self, db_manager):
        """Cleanup should return count of removed sessions."""
        # Create a guest with 0-day TTL (immediately expired is tricky,
        # but at minimum this exercises the cleanup path)
        db_manager.create_guest_session(ttl_days=7)
        count = db_manager.cleanup_expired_guests()
        # With a 7-day TTL, nothing should be expired yet
        assert count == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Presets
# ═══════════════════════════════════════════════════════════════════════════════

class TestPresets:
    """Test preset CRUD operations."""

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

    def test_update_preset_invalid_field(self, db_manager, sample_user, sample_preset):
        """Invalid fields should be ignored."""
        preset_id = db_manager.create_preset(user_id=sample_user["id"], **sample_preset)
        result = db_manager.update_preset(preset_id, nonexistent_field="value")
        assert result is False

    def test_increment_use_count(self, db_manager, sample_user, sample_preset):
        preset_id = db_manager.create_preset(user_id=sample_user["id"], **sample_preset)
        db_manager.increment_preset_use(preset_id)
        db_manager.increment_preset_use(preset_id)
        presets = db_manager.get_presets(sample_user["id"])
        assert presets[0]["use_count"] == 2

    def test_multiple_presets(self, db_manager, sample_user):
        db_manager.create_preset(
            sample_user["id"], "Preset A", "training",
            json.dumps({"rounds": 3}), "Desc A", "tag1",
        )
        db_manager.create_preset(
            sample_user["id"], "Preset B", "sparring",
            json.dumps({"rounds": 5}), "Desc B", "tag2",
        )
        presets = db_manager.get_presets(sample_user["id"])
        assert len(presets) == 2

    def test_favorite_presets_sorted_first(self, db_manager, sample_user):
        id_a = db_manager.create_preset(
            sample_user["id"], "Not Fav", "training",
            json.dumps({}), "", "",
        )
        id_b = db_manager.create_preset(
            sample_user["id"], "Is Fav", "training",
            json.dumps({}), "", "",
        )
        db_manager.update_preset(id_b, is_favorite=1)
        presets = db_manager.get_presets(sample_user["id"])
        assert presets[0]["name"] == "Is Fav"

    def test_no_presets_for_user(self, db_manager, sample_user):
        presets = db_manager.get_presets(sample_user["id"])
        assert presets == []


# ═══════════════════════════════════════════════════════════════════════════════
# Training Sessions
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrainingSessions:
    """Test session save and retrieve operations."""

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

    def test_session_detail_nonexistent(self, db_manager, sample_user):
        detail = db_manager.get_session_detail(sample_user["username"], "nonexistent_id")
        assert detail is None

    def test_filter_by_mode(self, db_manager, sample_user):
        db_manager.save_training_session(sample_user["username"], {
            "session_id": "s1", "mode": "training", "difficulty": "beginner"
        })
        db_manager.save_training_session(sample_user["username"], {
            "session_id": "s2", "mode": "sparring", "difficulty": "medium"
        })
        training = db_manager.get_session_history(sample_user["username"], mode="training")
        assert len(training) == 1

    def test_session_history_limit(self, db_manager, sample_user):
        for i in range(10):
            db_manager.save_training_session(sample_user["username"], {
                "session_id": f"s_{i}", "mode": "training", "difficulty": "beginner"
            })
        history = db_manager.get_session_history(sample_user["username"], limit=5)
        assert len(history) == 5

    def test_save_session_event(self, db_manager, sample_user, sample_session_data):
        db_manager.save_training_session(sample_user["username"], sample_session_data)
        db_manager.save_session_event(
            sample_user["username"],
            sample_session_data["session_id"],
            timestamp=1.0,
            event_type="punch",
            data={"type": "jab", "confidence": 0.88},
        )
        detail = db_manager.get_session_detail(
            sample_user["username"], sample_session_data["session_id"]
        )
        assert len(detail["events"]) == 1
        assert detail["events"][0]["event_type"] == "punch"

    def test_session_config_stored_as_json(self, db_manager, sample_user, sample_session_data):
        db_manager.save_training_session(sample_user["username"], sample_session_data)
        detail = db_manager.get_session_detail(
            sample_user["username"], sample_session_data["session_id"]
        )
        config = json.loads(detail["config_json"])
        assert config["combo"] == "jab-cross-hook"

    def test_upsert_session(self, db_manager, sample_user):
        """Saving the same session_id twice should update, not duplicate."""
        db_manager.save_training_session(sample_user["username"], {
            "session_id": "s1", "mode": "training", "difficulty": "beginner",
            "rounds_completed": 1,
        })
        db_manager.save_training_session(sample_user["username"], {
            "session_id": "s1", "mode": "training", "difficulty": "beginner",
            "rounds_completed": 3,
        })
        history = db_manager.get_session_history(sample_user["username"])
        assert len(history) == 1
        assert history[0]["rounds_completed"] == 3


# ═══════════════════════════════════════════════════════════════════════════════
# Gamification (via Database)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGamification:
    """Test XP, ranks, streaks, and achievements via the database."""

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
