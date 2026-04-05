# BoxBunny System Integration

## 1. Communication Paths

The BoxBunny system has four communication layers connecting the GUI (PySide6 touchscreen app), the Dashboard (phone/web app), and the ROS 2 Core (sensor processing and robot control).

```
+----------------+         ROS Topics/Services          +----------------+
|                | <----------------------------------> |                |
|   BoxBunny     |        GuiBridge (QThread)           |   ROS 2 Core   |
|   GUI          |                                      |   (10+ nodes)  |
|   (PySide6)    | <--- /tmp/ JSON files (100ms poll)   |                |
|                |                                      +----------------+
+-------+--------+
        |
        |  Shared JSON files in /tmp/
        |  Shared SQLite databases
        |
+-------+--------+
|                |
|   BoxBunny     |      REST API + WebSocket
|   Dashboard    | <------------------------------> Phone/Browser
|   (Backend)    |
|                |
+----------------+
```

### 1.1 GUI <-> ROS Core: GuiBridge

The `GuiBridge` class (`src/boxbunny_gui/boxbunny_gui/gui_bridge.py`) is the primary bridge between the PySide6 GUI and ROS 2. It runs a `_RosWorker` in a background **QThread** that spins a ROS 2 node (`boxbunny_gui` node).

**How it works**:
1. `GuiBridge.start()` creates a QThread and moves a `_RosWorker` object into it.
2. The worker initialises a ROS 2 node with `SingleThreadedExecutor` and subscribes to all relevant topics.
3. ROS callbacks on the worker emit **Qt Signals** (auto-queued across threads).
4. The GuiBridge forwards these signals to GUI page widgets connected on the main thread.
5. Service calls (StartSession, EndSession, GenerateLlm) use `call_async()` with done callbacks.

**Signals forwarded** (worker -> bridge -> GUI pages):

| Signal | Data | Source Topic |
|--------|------|-------------|
| `punch_confirmed` | dict (punch_type, pad, level, force, cv_confidence, imu_confirmed, cv_confirmed, accel_magnitude) | `/boxbunny/punch/confirmed` |
| `defense_event` | dict (arm, robot_punch_code, struck, defense_type) | `/boxbunny/punch/defense` |
| `drill_progress` | dict (combos_completed, combos_remaining, overall_accuracy, current_streak, best_streak) | `/boxbunny/drill/progress` |
| `session_state_changed` | (state: str, mode: str) | `/boxbunny/session/state` |
| `coach_tip` | (tip_text: str, tip_type: str) | `/boxbunny/coach/tip` |
| `nav_command` | command: str | `/boxbunny/imu/nav_event` |
| `imu_status` | dict (left_pad, centre_pad, right_pad, head_pad, left_arm, right_arm, is_simulator) | `/boxbunny/imu/status` |
| `cv_detection` | (punch_type: str, confidence: float) | `/boxbunny/cv/detection` |
| `strike_complete` | dict (punch_code, status, duration_ms) | `/boxbunny/robot/strike_complete` |
| `debug_info` | dict (action, confidence, consecutive, fps) | `/boxbunny/cv/debug_info` |

**Service wrappers**:

| Method | ROS Service | Purpose |
|--------|------------|---------|
| `call_start_session()` | `/boxbunny/session/start` | Begin a training session |
| `call_end_session()` | `/boxbunny/session/end` | End session, get summary JSON |
| `call_generate_llm()` | `/boxbunny/llm/generate` | Request AI coaching text |

**Publishers** (GUI -> ROS):

| Method | Topic | Purpose |
|--------|-------|---------|
| `publish_punch_command()` | `/boxbunny/robot/command` | Trigger a robot punch |
| `publish_height_command()` | `/boxbunny/robot/height` | Manual height adjustment (up/down/stop) |

**Offline mode**: If `rclpy` is not available (e.g., running GUI standalone for UI development), GuiBridge gracefully degrades -- all signals are suppressed, service calls return failure immediately.

### 1.2 GUI <-> Dashboard: Shared Files and Databases

The GUI and Dashboard Backend communicate indirectly through the filesystem:

**Shared JSON files in `/tmp/`**:
- `/tmp/boxbunny_gui_command.json` -- Remote commands from dashboard to GUI
- `/tmp/boxbunny_gui_login.json` -- Login state synchronisation
- `/tmp/boxbunny_height_state.json` -- Current height adjustment state

**Shared SQLite databases**:
- `data/boxbunny_main.db` -- User accounts, presets, coaching sessions (read by both GUI and dashboard)
- `data/users/{username}/boxbunny.db` -- Per-user training data (read by dashboard for analytics)

### 1.3 Dashboard Frontend <-> Backend

The Dashboard is a web application accessible via phone or browser.

- **REST API**: Standard HTTP endpoints for user authentication, session history, preset management, and analytics data.
- **WebSocket**: Real-time push for live training data updates (punch counts, round state, coaching tips) during active sessions.

### 1.4 Dashboard <-> ROS Core

The Dashboard does not communicate directly with ROS nodes. Instead:
1. **Outbound** (Dashboard -> Robot): Dashboard writes commands to `/tmp/boxbunny_gui_command.json`, which the GUI polls and executes via ROS service calls.
2. **Inbound** (Robot -> Dashboard): Session data is saved to SQLite by the GUI after each session. Dashboard reads from the shared database.

---

## 2. Remote Command Protocol

The Dashboard can remotely control the robot by writing JSON commands to a shared file that the GUI polls.

### File Location

```
/tmp/boxbunny_gui_command.json
```

### Polling Interval

The GUI polls this file every **100ms** (10 Hz).

### Command Format

```json
{
  "action": "start_training",
  "timestamp": "2026-04-06T14:30:00",
  "params": {
    "mode": "sparring",
    "difficulty": "intermediate",
    "rounds": 4,
    "work_time_sec": 180,
    "rest_time_sec": 60,
    "style": "boxer",
    "speed": "medium"
  }
}
```

### Supported Actions

| Action | Description | Params |
|--------|-------------|--------|
| `start_training` | Start a training session with specified config | `mode`, `difficulty`, `rounds`, `work_time_sec`, `rest_time_sec`, `speed` |
| `start_preset` | Launch a saved preset by ID | `preset_id` |
| `height_adjust` | Manual height adjustment | `direction` (up/down/stop) |
| `navigate` | Navigate the GUI to a specific page | `page` (home/training/sparring/settings/...) |

### Processing Flow

1. Dashboard backend writes command JSON to `/tmp/boxbunny_gui_command.json`.
2. GUI file watcher reads the file on next poll cycle (within 100ms).
3. GUI validates the command and clears the file.
4. GUI executes the appropriate action:
   - `start_training` / `start_preset` -> calls `GuiBridge.call_start_session()` ROS service.
   - `height_adjust` -> calls `GuiBridge.publish_height_command()`.
   - `navigate` -> triggers internal GUI page navigation.

---

## 3. Authentication Flow

### 3.1 GUI Authentication (Pattern Lock)

The GUI uses a 3x3 grid pattern lock for user authentication on the touchscreen.

1. User draws a pattern on the 3x3 grid (numbers 0-8 representing grid positions).
2. Pattern is converted to a string (e.g., `[0, 1, 2, 5, 8]` -> `"01258"`).
3. The string is hashed with **SHA-256**.
4. Hash is compared against the `pattern_hash` column in the `users` table of `boxbunny_main.db`.
5. On match, the user is logged in and their per-user database is loaded.

### 3.2 Dashboard Authentication (JWT)

The Dashboard uses standard JWT token authentication.

1. User submits username and password via the REST API.
2. Password is verified against `password_hash` in the `users` table.
3. On success, a JWT token is generated and stored in the `auth_sessions` table with:
   - `device_type`: "phone" or "robot"
   - `expires_at`: Token expiration timestamp
   - `is_active`: 1 (active)
4. The token is returned to the client and used in subsequent API requests via the Authorization header.

### 3.3 Shared User Database

Both GUI and Dashboard share the same `users` table in `data/boxbunny_main.db`:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,      -- Used by Dashboard (JWT auth)
    pattern_hash TEXT,                 -- Used by GUI (pattern lock)
    display_name TEXT NOT NULL,
    user_type TEXT NOT NULL,           -- 'individual' or 'coach'
    level TEXT NOT NULL,               -- 'beginner', 'intermediate', 'advanced'
    ...
);
```

### 3.4 Auto-Login from Phone

When a user logs in on the Dashboard and navigates to remote control:
1. Dashboard writes a login state file to `/tmp/boxbunny_gui_login.json` with the authenticated username.
2. GUI detects the login file and automatically logs in as that user.
3. This enables seamless "scan QR -> phone logged in -> robot ready" flow.

### 3.5 Guest Sessions

For users without accounts, a guest session token is created:
- Stored in the `guest_sessions` table with a 7-day TTL.
- Can be later "claimed" by a registered user via `claimed_by_user_id`.

---

## 4. Data Flow Examples

### 4.1 Training Session End-to-End

```
User taps "Start"     GUI calls StartSession     session_manager creates
on touchscreen    -->  service via GuiBridge  -->  session, publishes
                                                   SessionState: "countdown"
        |
        v
IMU mode switches      cv_node increases         Height auto-adjust
to TRAINING            frame rate to 30Hz         during countdown
        |
        v
SessionState: "active"  Punches flow:
        |               cv_node -> PunchDetection
        |               imu_node -> PunchEvent
        v               punch_processor fuses -> ConfirmedPunch
session_manager         session_manager accumulates all data
accumulates punches     drill_manager validates combos (training mode)
        |               sparring_engine attacks (sparring mode)
        v               llm_node publishes coaching tips every ~18s
Round ends (work_time elapsed)
        |
        v
All rounds complete --> session_manager builds summary
                       (total_punches, distributions, defense_rate,
                        movement, enriched fields)
                        |
                        v
                   SessionState: "complete"
                   SessionPunchSummary published
                        |
                        v
                   GUI receives summary via EndSession service
                   Saves to per-user SQLite database
                   Displays results page
                        |
                        v
                   Dashboard can read session data from
                   data/users/{username}/boxbunny.db
                   via REST API on next page load
```

### 4.2 Remote Preset Launch from Phone

```
User opens Dashboard    Selects a preset        Dashboard backend writes
on phone browser   -->  and taps "Launch"   -->  command to /tmp/:
                                                  {
                                                    "action": "start_preset",
                                                    "params": {"preset_id": 5}
                                                  }
        |
        v (within 100ms)
GUI polls /tmp/boxbunny_gui_command.json
GUI reads preset config from boxbunny_main.db
GUI navigates to training page
GUI calls StartSession service with preset config
        |
        v
Normal training session flow begins
Phone shows live updates via WebSocket
```

### 4.3 Coach Station with Participants

```
Coach Sarah logs in     Selects "Coach Station"    Sets student count
(pattern lock)     -->  from main menu        -->  (e.g., 6 students)
        |
        v
Participant 1 taps GO or hits centre pad
        |
        v
Timer starts for Participant 1
Training runs for configured work_time
        |
        v
Timer ends --> Auto-advance to Participant 2
Participant 2 taps GO or hits centre pad
        |
        v
... repeats for all participants ...
        |
        v
All participants complete
Session results saved to coaching_sessions + coaching_participants
        |
        v
Coach sees group summary:
  - Per-participant punch counts, distributions
  - Reaction times, fatigue indexes
  - Overall group statistics

Dashboard can display coaching history:
  coaching_sessions JOIN coaching_participants
  WHERE coach_user_id = sarah.id
```

### 4.4 Data Persistence Architecture

```
During session:
  session_manager autosaves every 10s (crash recovery)

At session end:
  GUI receives summary_json from EndSession service response
  GUI writes to per-user database:
    training_sessions (session metadata + summary_json)
    session_events (timestamped events)
    combo_progress (updated drill accuracy/mastery)
    sparring_sessions (if sparring mode)
    sparring_weakness_profile (updated defense rates)
    user_xp (XP awarded)
    achievements (newly unlocked)
    streaks (updated streak counters)
    personal_records (checked and updated)

Dashboard reads:
  Main DB: users, presets, coaching_sessions
  Per-user DBs: all tables for analytics display
```
