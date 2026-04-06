# GUI and Dashboard Communication Reference

> Complete reference for recreating the GUI/Dashboard communication diagram — every component, API route, IPC file, and data flow.

---

## 1. System Overview

| Component | Technology | Location | Port |
|---|---|---|---|
| Phone Frontend | Vue 3 SPA (Tailwind CSS, Pinia) | Browser via WiFi | 8080 |
| FastAPI Backend | Python, Uvicorn | Jetson Orin NX | 8080 |
| Desktop GUI | PySide6 (QStackedWidget) | Jetson Orin NX | Local |
| ROS 2 Core | DDS messaging | Jetson Orin NX | DDS |
| Main Database | SQLite | data/boxbunny_main.db | File |
| User Databases | SQLite (per-user) | data/users/{name}/boxbunny.db | File |

---

## 2. Phone / Vue 3 SPA

### 2.1 Pinia Stores

| Store | State | Key Methods |
|---|---|---|
| **auth** | user, token (localStorage `bb_token`), isAuthenticated, isCoach | login(), signup(), logout(), initialize() |
| **websocket** | ws, connected, reconnectAttempts (max 10) | connect(), disconnect(), send(), on(), startPing() (30s) |
| **session** | currentSession, isActive, liveState, history, gamification | fetchCurrentSession(), fetchHistory(), fetchGamification() |
| **chat** | messages, sending, streaming (word-by-word 20ms) | loadHistory(), sendMessage(), clearMessages() |

### 2.2 API Client

- **Base URL:** `/api` (relative, same-origin)
- **Auth:** `Authorization: Bearer {token}` on every request
- **Token storage:** `localStorage['bb_token']`
- **Error handling:** Throws `ApiError(status, message, data)`

### 2.3 Vue Router Pages

| Route | View | Auth Required |
|---|---|---|
| `/login` | LoginView | No |
| `/` | DashboardView | Yes |
| `/session/:id` | SessionDetailView | Yes |
| `/history` | HistoryView | Yes |
| `/performance` | PerformanceView | Yes |
| `/achievements` | AchievementsView | Yes |
| `/chat` | ChatView | Yes |
| `/training` | TrainingView | Yes |
| `/presets` | PresetsView | Yes |
| `/settings` | SettingsView | Yes |
| `/coach` | CoachView | Yes + Coach role |

---

## 3. FastAPI Backend — All API Routes

### 3.1 Authentication (`/api/auth`)

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| GET | `/auth/users` | - | `[{id, username, display_name, level, user_type, has_pattern}]` | No auth, account picker |
| POST | `/auth/login` | `{username, password, device_type}` | `{token, user_id, username, display_name, user_type}` | Writes `/tmp/boxbunny_gui_login.json` |
| POST | `/auth/signup` | `{username, password, display_name, user_type, level}` | Token + user info | Creates user + notifies GUI |
| POST | `/auth/pattern-login` | `{username, pattern:[int]}` | Token + user info | GUI-synced pattern lock |
| GET | `/auth/session` | - | User profile object | Token validation |
| PUT | `/auth/profile` | `{display_name?, level?, age?, ...}` | `{status: 'ok'}` | Update profile |
| POST | `/auth/set-pattern` | `{user_id, pattern:[int]}` | `{status: 'ok'}` | Set pattern lock |
| DELETE | `/auth/logout` | - | 204 | Invalidates token |

### 3.2 Sessions (`/api/sessions`)

| Method | Path | Params | Response |
|---|---|---|---|
| GET | `/sessions/current` | - | `{active, session, live_state?}` |
| GET | `/sessions/history` | `page, page_size, mode` | `{sessions, total, page, page_size}` |
| GET | `/sessions/{id}` | - | Full session detail |
| GET | `/sessions/{id}/raw` | - | Raw JSON data |
| GET | `/sessions/trends` | `range=7d\|30d\|90d\|all` | Aggregated analytics |

### 3.3 Chat (`/api/chat`)

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/chat/status` | - | `{ready, model}` |
| POST | `/chat/message` | `{message, context}` | `{reply, timestamp, actions?, suggestions?}` |
| GET | `/chat/history` | `limit=50` | `[{role, content, timestamp}]` |

**Chat → LLM flow:** POST `/chat/message` → build system prompt with training history → call ROS `/boxbunny/llm/generate` service → parse response for `[DRILL:...]` action tags → return reply + actions

### 3.4 Remote Control (`/api/remote`)

| Method | Path | Body | Response | IPC File |
|---|---|---|---|---|
| POST | `/remote/command` | `{action, config}` | `{success, message}` | `/tmp/boxbunny_gui_command.json` |
| POST | `/remote/height` | `{action: up\|down\|stop}` | `{success, message}` | `/tmp/boxbunny_height_cmd.json` |
| GET | `/remote/presets` | - | User's presets | No IPC |

**Remote command actions:**
| Action | Config Fields | GUI Result |
|---|---|---|
| `start_training` | mode, difficulty, config | Navigate to training_session |
| `start_preset` | full preset config | Navigate to training_config |
| `open_presets` | {} | Show preset overlay |
| `setup_drill` | combo, difficulty | Navigate to training_config |
| `navigate` | route, username | Router.navigate(route) |

### 3.5 Gamification (`/api/gamification`)

| Method | Path | Response |
|---|---|---|
| GET | `/gamification/profile` | `{total_xp, current_rank, xp_to_next_rank, current_streak, personal_records}` |
| GET | `/gamification/achievements` | `[{achievement_id, unlocked_at}]` |
| GET | `/gamification/leaderboard/{id}` | `[{username, display_name, score, rank}]` |
| GET | `/gamification/benchmarks` | Demographic peer comparison |

**XP formula:** `(50 + rounds*15 + completion_bonus) * mode_mult * difficulty_mult` (min 10)

**Ranks:** Novice(0) → Contender(500) → Fighter(1500) → Warrior(4000) → Champion(10000) → Elite(25000)

### 3.6 Presets (`/api/presets`)

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/presets/` | - | `[{id, name, config_json, is_favorite}]` |
| POST | `/presets/` | `{name, preset_type, config_json, description, tags}` | Preset object |
| PUT | `/presets/{id}` | `{name?, config_json?}` | `{id, updated}` |
| DELETE | `/presets/{id}` | - | `{id, archived}` |
| POST | `/presets/{id}/favorite` | - | `{id, favorite}` |

### 3.7 Coach (`/api/coach`) — requires coach role

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/coach/load-config` | `{preset_id}` | `{loaded, config}` |
| POST | `/coach/start-station` | `{name, preset_id?, config}` | `{coaching_session_id, started_at}` |
| POST | `/coach/end-session` | `{coaching_session_id}` | `{ended_at, participant_count}` |
| GET | `/coach/live` | - | `[{username, rounds_completed, score, connected}]` |
| GET | `/coach/sessions` | - | `[{session_id, name, started_at, ended_at}]` |

### 3.8 Export (`/api/export`)

| Method | Path | Response |
|---|---|---|
| GET | `/export/session/{id}/csv` | CSV file stream |
| GET | `/export/session/{id}/pdf` | PDF file stream |
| GET | `/export/range` | Aggregated CSV/PDF (date range + mode filter) |

---

## 4. WebSocket Server

**Endpoint:** `GET /ws?user_id={id}&role={role}`

**Ping:** Client sends every 30s to keep alive

**Auto-Reconnect:** Exponential backoff (max 30s), up to 10 attempts

**State buffering:** On reconnect, server sends last known state via `state_sync` event

### Message Events

| Event | Direction | Data |
|---|---|---|
| `session_started` | Server→Client | `{session_id, mode, difficulty, started_at, rounds_total, work_time_sec, rest_time_sec}` |
| `session_stats` | Server→Client | `{session_id, rounds_completed, total_punches, avg_accuracy, current_streak, last_punch}` |
| `session_completed` | Server→Client | `{session_id, ended_at, is_complete, summary_json}` |
| `config_changed` | Server→Client | `{preset_id, config}` (coach broadcast) |
| `user_authenticated` | Server→Client | `{user_id, username, timestamp}` |
| `state_sync` | Server→Client | Last broadcasted state (on reconnect) |
| `ping` / `pong` | Both | Keep-alive |

**Message format:**
```json
{"event": "...", "data": {...}, "timestamp": "ISO datetime"}
```

---

## 5. IPC Files (Backend → GUI)

### 5.1 Login Notification

**File:** `/tmp/boxbunny_gui_login.json`
**Writer:** FastAPI (on login/signup/pattern-login)
**Reader:** GUI polls every 100ms, deletes after reading
```json
{
  "user_id": 123,
  "username": "alice",
  "display_name": "Alice Smith",
  "user_type": "individual"
}
```
**Effect:** GUI auto-navigates to home page for that user

### 5.2 Remote GUI Command

**File:** `/tmp/boxbunny_gui_command.json`
**Writer:** FastAPI `/api/remote/command`
**Reader:** GUI polls every 100ms, deletes after reading
```json
{
  "action": "start_training",
  "config": {"mode": "sparring", "difficulty": "intermediate"},
  "username": "alice",
  "timestamp": 1234567890.123
}
```
**Effect:** GUI executes the action (navigate, start session, show overlay, etc.)

### 5.3 Height Control

**File:** `/tmp/boxbunny_height_cmd.json`
**Writer:** FastAPI `/api/remote/height` (continuous while button held)
**Reader:** GUI polls every 100ms, **never deletes** (overwrites only)
```json
{
  "action": "manual_up",
  "timestamp": 1234567890.123
}
```
**Stale timeout:** If timestamp > 500ms old, GUI auto-stops (safety)
**Effect:** GUI publishes HeightCommand to ROS

---

## 6. PySide6 Desktop GUI

### 6.1 Architecture

```
BoxBunnyApp
  ├── QMainWindow (1024x600, frameless option)
  │     └── QGraphicsView (scaling for fullscreen)
  │           └── QStackedWidget (24 pages)
  │
  ├── GuiBridge (ROS 2 background thread)
  │     └── _RosWorker (QThread, SingleThreadedExecutor)
  │           ├── 10 ROS subscriptions → Qt signals
  │           ├── 2 ROS publishers
  │           └── 3 ROS service clients
  │
  ├── PageRouter (navigation with kwargs)
  ├── SoundManager (audio playback)
  ├── ImuNavHandler (pad navigation)
  ├── RemoteCommandPoller (QTimer, 100ms)
  ├── DevOverlay (F12)
  └── PresetOverlay (quick-launch)
```

### 6.2 All 24 GUI Pages

| # | Route | Page | Description |
|---|---|---|---|
| 0 | auth | StartupPage | Account picker / login |
| 1 | home | HomeIndividualPage | Individual dashboard |
| 2 | home_guest | HomeGuestPage | Guest dashboard |
| 3 | home_coach | HomeCoachPage | Coach dashboard |
| 4 | guest_assessment | GuestAssessmentPage | Proficiency quiz |
| 5 | account_picker | AccountPickerPage | Select account |
| 6 | pattern_lock | PatternLockPage | Pattern entry |
| 7 | signup | SignupPage | New account |
| 8 | training_select | ComboSelectPage | Drill selection |
| 9 | training_config | TrainingConfigPage | Rounds/work/rest setup |
| 10 | training_session | TrainingSessionPage | Live training |
| 11 | training_rest | TrainingRestPage | Rest countdown |
| 12 | training_results | TrainingResultsPage | Session summary |
| 13 | self_select | SelfSelectPage | Free training launch |
| 14 | sparring_select | SparringConfigPage | Sparring config |
| 15 | sparring_session | SparringSessionPage | Live sparring |
| 16 | sparring_results | SparringResultsPage | Sparring summary |
| 17 | performance | PerformanceMenuPage | Test menu |
| 18 | power_test | PowerTestPage | Max force test |
| 19 | stamina_test | StaminaTestPage | Endurance test |
| 20 | reaction_test | ReactionTestPage | Reaction time test |
| 21 | history | HistoryPage | Past sessions |
| 22 | presets | PresetsPage | Preset management |
| 23 | coach | StationPage | Coach station |
| 24 | settings | SettingsPage | User preferences |

### 6.3 GuiBridge — ROS 2 Thread

**Subscriptions (ROS → Qt signals):**
| Topic | Signal | Data |
|---|---|---|
| `/boxbunny/punch/confirmed` | `punch_confirmed(dict)` | punch_type, pad, level, force, cv_confidence, imu/cv_confirmed, accel |
| `/boxbunny/punch/defense` | `defense_event(dict)` | arm, robot_punch_code, struck, defense_type |
| `/boxbunny/drill/progress` | `drill_progress(dict)` | combos_completed/remaining, accuracy, streak |
| `/boxbunny/session/state` | `session_state_changed(str, str)` | (state, mode) |
| `/boxbunny/coach/tip` | `coach_tip(str, str)` | (tip_text, tip_type) |
| `/boxbunny/imu/nav_event` | `nav_command(str)` | prev, next, enter, back |
| `/boxbunny/imu/status` | `imu_status(dict)` | 4 pad + 2 arm connection bools |
| `/boxbunny/robot/strike_complete` | `strike_complete(dict)` | JSON robot feedback |
| `/boxbunny/cv/detection` | `cv_detection(str, float)` | (punch_type, confidence) |
| `/boxbunny/cv/debug_info` | `debug_info(dict)` | CV pipeline debug JSON |

**Publishers (GUI → ROS):**
| Topic | Message | Method |
|---|---|---|
| `/boxbunny/robot/command` | RobotCommand | `publish_punch_command(code, speed, source)` |
| `/boxbunny/robot/height` | HeightCommand | `publish_height_command(action)` |

**Service Clients (GUI → ROS, async):**
| Service | Type | Method |
|---|---|---|
| `/boxbunny/session/start` | StartSession | `call_start_session(mode, difficulty, config_json, username, callback)` |
| `/boxbunny/session/end` | EndSession | `call_end_session(session_id, callback)` |
| `/boxbunny/llm/generate` | GenerateLlm | `call_generate_llm(prompt, context_json, system_prompt_key, callback)` |

### 6.4 Input Methods

| Input | Source | Description |
|---|---|---|
| Touch | Touchscreen | Direct Qt touch events |
| IMU Pad Nav | `/boxbunny/imu/nav_event` | Left=prev, Right=next, Centre=enter, Head=back |
| Keyboard | USB keyboard | Arrows + Enter + Escape + F11 (fullscreen) + F12 (debug) |
| Phone Remote | IPC files | Commands from phone dashboard |

---

## 7. Database Schema

### 7.1 Main DB (`boxbunny_main.db`)

| Table | Key Fields | Purpose |
|---|---|---|
| **users** | id, username, password_hash, pattern_hash, display_name, user_type, level, age, gender, height_cm, weight_kg, reach_cm, stance | User accounts |
| **auth_sessions** | user_id, session_token, device_type, expires_at, is_active | Bearer tokens (7-day expiry) |
| **guest_sessions** | guest_session_token, claimed_by_user_id | Guest-to-user linking |
| **presets** | user_id, name, preset_type, config_json, is_favorite, tags, use_count | Training presets |
| **coaching_sessions** | coach_user_id, station_config_preset_id, started_at, ended_at | Coach sessions |
| **coaching_participants** | coaching_session_id, participant_name, session_data_json | Per-participant data |

**Accessed by:** FastAPI (DatabaseManager), GUI (db_helper.py)

### 7.2 Per-User DB (`users/{name}/boxbunny.db`)

| Table | Key Fields | Purpose |
|---|---|---|
| **training_sessions** | session_id, mode, difficulty, rounds, config_json, summary_json | Session records |
| **session_events** | session_id, event_type, data_json | Punch/defense events |
| **combo_progress** | combo_id, attempts, best_accuracy, mastered | Drill mastery |
| **power_tests** | peak_force, avg_force, punch_count | Power test results |
| **stamina_tests** | duration_sec, total_punches, fatigue_index | Stamina results |
| **reaction_tests** | avg_reaction_ms, best_reaction_ms, tier | Reaction results |
| **sparring_sessions** | style, defense_rate, punch_distribution_json | Sparring records |
| **sparring_weakness_profile** | punch_type, defense_success_rate | AI targeting data |
| **user_xp** | total_xp, current_rank | XP/rank |
| **personal_records** | record_type, value, achieved_at | Best scores |
| **achievements** | achievement_id, unlocked_at | Unlocked badges |
| **streaks** | current_streak, longest_streak, weekly_goal/progress | Training consistency |

**Accessed by:** FastAPI (DatabaseManager read), ROS session_manager (write), GUI (db_helper.py read)

---

## 8. Authentication Flow

### Phone Login
```
1. Phone: POST /api/auth/login {username, password}
2. Backend: verify_password() → create_auth_session() → token (7-day expiry)
3. Backend: write /tmp/boxbunny_gui_login.json {username, display_name}
4. Phone: stores token in localStorage['bb_token']
5. GUI: polls /tmp file → reads → deletes → navigates to home page
```

### Token Format
- Random 32-byte URL-safe string
- Stored in `auth_sessions` table
- Validated: `WHERE session_token=? AND is_active=1 AND expires_at > now`
- Expires: 168 hours (7 days)

---

## 9. Complete Data Flows (for diagram)

### Training Session (Phone → GUI → ROS)
```
Phone: tap "Start Training"
  → POST /api/remote/command {action:"start_training", config:{...}}
  → Backend writes /tmp/boxbunny_gui_command.json
  → GUI polls (100ms), reads, deletes file
  → GUI calls bridge.call_start_session() (ROS Service)
  → session_manager creates session, transitions IDLE→COUNTDOWN
  → SessionState published to all nodes
  → GUI navigates to training_session page
  → WebSocket broadcasts session_started to phone
  → Phone shows live stats
```

### Chat / LLM
```
Phone: type message in ChatView
  → POST /api/chat/message {message:"How's my jab?"}
  → Backend builds system prompt with user's training history
  → Backend calls ROS /boxbunny/llm/generate service (async)
  → llm_node runs Qwen 2.5 3B inference
  → Returns reply text (may contain [DRILL:...] action tags)
  → Backend parses actions, returns {reply, actions, suggestions}
  → Phone streams response word-by-word (20ms/word)
```

### Height Control (Press & Hold)
```
Phone: press height up button
  → Repeated POST /api/remote/height {action:"manual_up"}
  → Backend writes /tmp/boxbunny_height_cmd.json (overwrite, never delete)
  → GUI polls (100ms), reads timestamp
  → If timestamp < 500ms old: publish HeightCommand to ROS
  → If timestamp >= 500ms old: auto-stop (safety)
  → robot_node receives HeightCommand, controls Teensy motor
Phone: release button
  → POST /api/remote/height {action:"stop"}
```

### Phone Login → GUI Sync
```
Phone: login with username + password
  → POST /api/auth/login
  → Backend writes /tmp/boxbunny_gui_login.json
  → GUI polls (100ms), reads, deletes
  → GUI navigates to home page for that user
  → WebSocket connects with user_id
  → Phone receives state_sync if session active
```
