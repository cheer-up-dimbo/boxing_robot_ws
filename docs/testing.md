# BoxBunny Testing Infrastructure

## Overview

BoxBunny uses a multi-tier testing strategy: unit tests via pytest, integration tests via Python scripts, and operational testing via Jupyter notebook cells.

---

## 1. Unit Tests (pytest)

**Location:** `tests/unit/`
**Run:** `python3 -m pytest tests/ -v`
**Total:** 146 tests across 3 files

### test_punch_fusion.py

Tests the CV+IMU sensor fusion pipeline (`boxbunny_core/punch_fusion.py`):

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestRingBuffer` | 7 | Ring buffer operations, maxlen eviction, time-based expiry, pop_match within window |
| `TestCVIMUFusion` | 3 | CV+IMU matching within fusion window, no match outside window, closest-first matching |
| `TestPadConstraints` | 10 | Punch-to-pad validity (jab→centre, left_hook→left, right_hook→right, all→head) |
| `TestReclassification` | 8 | Invalid punch reclassification via secondary confidence, min confidence thresholds |
| `TestExpiredEvents` | 4 | CV/IMU event expiry, expire all, expire none |
| `TestDefenseClassification` | 8 | Block (CV), slip (lateral), dodge (depth), hit (contact), priority ordering |
| `TestSessionStats` | 4 | Punch recording, multi-punch accumulation, peak force tracking, defense recording |

### test_gamification.py

Tests the XP and ranking system (`boxbunny_core/gamification.py`):

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestRankSystem` | 10 | All 6 rank tiers (Novice→Elite), boundary values, XP-to-next calculations |
| `TestSessionXP` | 7 | Base XP per mode, completion bonus, score multiplier, streak bonus, minimum floor |
| `TestSessionScore` | 5 | Perfect score, zero score, partial scores, boundary conditions |
| `TestAchievements` | 5 | Achievement unlock conditions, duplicate prevention, listing |
| `TestLeaderboard` | 3 | Ranking computation, tie-breaking, empty boards |

### test_database.py

Tests the database manager (`boxbunny_dashboard/db/manager.py`):

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestUserManagement` | 13 | Create, duplicate prevention, password verify, get user, list users, coach user type |
| `TestPatternLock` | 5 | Set/verify pattern, wrong pattern, no pattern, overwrite, hash format (SHA-256) |
| `TestGuestSessions` | 5 | Create, multiple, claim, double-claim prevention, expiry cleanup |
| `TestPresets` | 7 | Create, update, invalid field rejection, use count, multiple, favorites sorting |
| `TestTrainingSessions` | 8 | Save/retrieve, detail, nonexistent, mode filter, limit, events, config JSON, upsert |
| `TestGamification` | 7 | Add XP, rank progression, personal records (new/broken/not broken), streaks, achievements |

### Test Fixtures (conftest.py)

12 shared pytest fixtures providing:

- `db_manager` — Fresh DatabaseManager with temp directory per test
- `sample_user` — Test user (testuser/testpass123)
- `sample_profiles` — Beginner Bob, Intermediate Ida, Coach Charlie
- `sample_session` — Training session with 87 punches
- `sample_sparring_session` — Sparring session with 210 punches
- `sample_punch_events` — CV detections + IMU impacts + confirmed punches
- `sample_defense_data` — Defense evaluation scenarios

---

## 2. Integration Tests

**Location:** `notebooks/scripts/test_integration.py`
**Run:** `python3 notebooks/scripts/test_integration.py`
**Total:** 28 tests

These test cross-module integration without requiring hardware:

- Config loading and YAML validation
- Pad-location constraint mapping (which punches valid on which pads)
- CV+IMU fusion algorithm correctness
- ROS message field verification (all 21 messages)
- Motor protocol validation (punch codes 1-6)
- Reaction time detection logic
- Punch sequence file parsing

---

## 3. Notebook-Based Testing

The Jupyter notebook (`notebooks/boxbunny_runner.ipynb`) provides operational testing cells:

| Cell | Purpose | Requirements |
|------|---------|-------------|
| 1b | Unit tests (full pytest suite) | None |
| 1c | Integration tests (28 tests) | None |
| 1d | Hardware check (camera, CUDA, models, DB) | Hardware |
| 4a | CV model live test | RealSense + conda |
| 4b | Reaction time test | cv_node running |
| 4c | CV+IMU fusion test | RealSense + Teensy |
| 5b | LLM coach test | LLM model file |
| 5c | Sound test (18 effects) | Audio output |
| 5e | Benchmark test (percentile calculations) | None |

---

## 4. Running Tests

```bash
# Full test suite
python3 -m pytest tests/ -v

# Specific test file
python3 -m pytest tests/unit/test_punch_fusion.py -v

# Specific test class
python3 -m pytest tests/unit/test_database.py::TestPatternLock -v

# With coverage
python3 -m pytest tests/ -v --cov=boxbunny_core --cov=boxbunny_dashboard

# Integration tests
python3 notebooks/scripts/test_integration.py
```

---

## 5. Test Data

Demo data can be seeded for manual testing:

```bash
python3 tools/demo_data_seeder.py          # Seed data
python3 tools/demo_data_seeder.py --clean   # Wipe and reseed
```

Creates 4 demo users with realistic training histories:

| User | Password | Level | Sessions | Tests | Achievements |
|------|----------|-------|----------|-------|-------------|
| alex | boxing123 | Beginner | 8 | 2 | 3 |
| maria | boxing123 | Intermediate | 35 | 5 | 8 |
| jake | boxing123 | Advanced | 120 | 15 | 15 |
| sarah | coaching123 | Coach | 3 classes | - | - |
