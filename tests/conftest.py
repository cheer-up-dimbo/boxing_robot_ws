"""Shared test fixtures for BoxBunny tests.

All fixtures use mock data — no hardware or ROS required.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add source paths for imports
WS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS_ROOT / "src" / "boxbunny_dashboard"))
sys.path.insert(0, str(WS_ROOT / "src" / "boxbunny_core"))
sys.path.insert(0, str(WS_ROOT / "action_prediction"))


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Temporary data directory with schema files."""
    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()
    src_schema = WS_ROOT / "data" / "schema"
    for sql_file in src_schema.glob("*.sql"):
        (schema_dir / sql_file.name).write_text(sql_file.read_text())
    return tmp_path


@pytest.fixture
def db_manager(tmp_data_dir):
    """Database manager with temporary databases."""
    from boxbunny_dashboard.db.manager import DatabaseManager
    return DatabaseManager(str(tmp_data_dir))


@pytest.fixture
def sample_user(db_manager):
    """Create and return a sample user."""
    user_id = db_manager.create_user(
        username="testuser",
        password="testpass123",
        display_name="Test User",
        user_type="individual",
        level="beginner",
    )
    return {"id": user_id, "username": "testuser", "display_name": "Test User"}


@pytest.fixture
def sample_session_data():
    """Sample training session data."""
    return {
        "session_id": "test_session_001",
        "mode": "training",
        "difficulty": "beginner",
        "started_at": "2026-03-29T10:00:00",
        "ended_at": "2026-03-29T10:15:00",
        "is_complete": True,
        "rounds_completed": 3,
        "rounds_total": 3,
        "work_time_sec": 180,
        "rest_time_sec": 60,
        "config": {"combo": "jab-cross-hook", "speed": "medium"},
        "summary": {
            "total_punches": 87,
            "punch_distribution": {"jab": 35, "cross": 30, "left_hook": 22},
            "defense_rate": 0.75,
            "avg_depth": 1.5,
        },
    }


@pytest.fixture
def sample_punch_events():
    """Sample confirmed punch events."""
    return [
        {"type": "jab", "pad": "centre", "force": 0.66, "cv_conf": 0.85, "ts": 1.0},
        {"type": "cross", "pad": "centre", "force": 1.0, "cv_conf": 0.92, "ts": 1.5},
        {"type": "left_hook", "pad": "right", "force": 0.33, "cv_conf": 0.78, "ts": 2.1},
        {"type": "jab", "pad": "centre", "force": 0.66, "cv_conf": 0.88, "ts": 3.0},
        {"type": "cross", "pad": "left", "force": 1.0, "cv_conf": 0.91, "ts": 3.4},
    ]


@pytest.fixture
def sample_preset():
    """Sample preset data."""
    return {
        "name": "Quick Jab Drill",
        "preset_type": "training",
        "config_json": json.dumps({
            "combo": "jab-cross",
            "rounds": 3,
            "work_time_sec": 120,
            "rest_time_sec": 45,
            "speed": "medium",
            "difficulty": "beginner",
        }),
        "description": "A quick jab-cross drill for warmup",
        "tags": "warmup,beginner",
    }
