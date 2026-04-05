# BoxBunny Dashboard -- Backend Documentation

## 1. Server Architecture

**File:** `src/boxbunny_dashboard/boxbunny_dashboard/server.py`

The backend is a FastAPI application served by Uvicorn, designed for local network
access via the BoxBunny WiFi access point (phones connect over the robot's AP).

### Application Factory

`create_app()` builds the FastAPI instance with:

- **Title:** BoxBunny Dashboard
- **Version:** 1.0.0
- **Lifespan:** `asynccontextmanager` that initialises `DatabaseManager` and
  `ConnectionManager` on startup and logs on shutdown.

### CORS Configuration

Wide-open CORS to allow any phone on the local network:

```
allow_origins=["*"]
allow_credentials=True
allow_methods=["*"]
allow_headers=["*"]
```

### Static File Serving (Vue SPA)

The built Vue SPA lives in `static/dist/`. The server:

1. Mounts `/assets` as a `StaticFiles` directory (JS/CSS bundles).
2. Registers a catch-all `GET /{full_path:path}` handler that:
   - Returns the literal file if it exists in `static/dist/`.
   - Otherwise falls back to `index.html` for client-side routing.
   - Returns a 404 JSON message if the frontend has not been built.

### Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `BOXBUNNY_DATA_DIR` | `<workspace>/data` | Root for SQLite databases |
| `BOXBUNNY_HOST` | `0.0.0.0` | Bind address |
| `BOXBUNNY_PORT` | `8080` | Listen port |

### Entry Point

```
uvicorn boxbunny_dashboard.server:app --host 0.0.0.0 --port 8080
```

The module-level `app = create_app()` is the ASGI target.

### Router Prefixes

| Router | Prefix | Tags |
|---|---|---|
| auth | `/api/auth` | auth |
| sessions | `/api/sessions` | sessions |
| presets | `/api/presets` | presets |
| gamification | `/api/gamification` | gamification |
| coach | `/api/coach` | coach |
| chat | `/api/chat` | chat |
| export | `/api/export` | export |
| remote | `/api/remote` | remote |

WebSocket endpoint: `/ws`

Health check: `GET /api/health` returns `{"status": "ok", "service": "boxbunny_dashboard"}`.

---

## 2. Authentication

**File:** `src/boxbunny_dashboard/boxbunny_dashboard/api/auth.py`

### Password Hashing

Passwords are hashed with **SHA-256 + random salt** (format: `sha256:<salt>:<hex_hash>`).
The same scheme is used by the desktop GUI so either can create accounts that the other
accepts. Legacy bcrypt hashes are also supported for backward compatibility:
`verify_password` checks the hash prefix and dispatches accordingly. Comparison uses
`hmac.compare_digest` to avoid timing attacks.

### Pattern Lock Hashing

Pattern sequences (list of integers) are joined with `-` and hashed identically to
passwords (SHA-256 + salt). Verification also supports legacy bcrypt hashes.

### Session Tokens

- Generated with `secrets.token_urlsafe(32)`.
- Stored in the `auth_sessions` table with `is_active` flag and `expires_at` timestamp.
- Default TTL: **168 hours (7 days)**.
- Validation joins `auth_sessions` with `users` and checks `is_active = 1` and
  `expires_at > datetime('now')`.

### Bearer Token Flow

All authenticated endpoints use the `get_current_user` dependency:

1. Extract `Authorization: Bearer <token>` header.
2. Call `db.validate_session_token(token)`.
3. Return the full user dict (id, username, display_name, user_type, level,
   age, gender, height_cm, weight_kg, reach_cm, stance) or raise 401.

### GUI Auto-Login

On successful login/signup/pattern-login, the server writes user info to
`/tmp/boxbunny_gui_login.json` so the desktop GUI can detect the login and
auto-navigate to the home screen.

---

## 3. API Routers

### 3.1 auth.py -- `/api/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/users` | No | List all registered users for the account picker. Returns `id`, `username`, `display_name`, `level`, `user_type`, `has_pattern`. |
| `POST` | `/login` | No | Authenticate with `username` + `password` + `device_type` (default `"phone"`). Returns `TokenResponse` (token, user_id, username, display_name, user_type). |
| `POST` | `/pattern-login` | No | Authenticate with `username` + `pattern` (list of ints, min length 4). Returns `TokenResponse`. |
| `POST` | `/signup` | No | Create account. Body: `username` (3-64), `password` (min 6), `display_name`, `user_type` (default `"individual"`), `level` (default `"beginner"`). Returns 201 + `TokenResponse`. 409 if username taken. |
| `POST` | `/pattern-verify` | No | Verify a pattern by `user_id` + `pattern`. Returns `TokenResponse`. |
| `POST` | `/guest-claim` | No | Link a guest session to a new account. Body: `guest_token`, `username`, `password`, `display_name`. Returns `TokenResponse`. |
| `GET` | `/session` | Yes | Validate current token and return `UserInfoResponse` (user_id, username, display_name, user_type, level, avatar, age, gender, height_cm, weight_kg, reach_cm, stance). |
| `PUT` | `/profile` | Yes | Update profile fields. Body: any subset of `display_name`, `level`, `avatar`, `proficiency_answers_json`, `age`, `gender`, `height_cm`, `weight_kg`, `reach_cm`, `stance`. Returns `{"status": "ok"}`. |
| `POST` | `/set-pattern` | Yes | Set/update pattern lock. Body: `user_id`, `pattern` (min 4 dots). Returns `{"status": "ok"}`. |
| `DELETE` | `/logout` | Yes* | Invalidate the current session token. Returns 204 No Content. (*reads token from header directly) |

#### Request/Response Models

**LoginRequest:** `username` (str), `password` (str), `device_type` (str, default "phone")

**SignupRequest:** `username` (str, 3-64), `password` (str, min 6), `display_name` (str, 1-128), `user_type` (str, default "individual"), `level` (str, default "beginner")

**PatternLoginRequest:** `username` (str), `pattern` (List[int], min 4)

**PatternVerifyRequest:** `user_id` (int), `pattern` (List[int], min 4)

**GuestClaimRequest:** `guest_token` (str), `username` (str), `password` (str), `display_name` (str)

**TokenResponse:** `token` (str), `user_id` (int?), `username` (str?), `display_name` (str?), `user_type` (str?)

**ProfileUpdateRequest:** `display_name`, `level`, `avatar`, `proficiency_answers_json`, `age`, `gender`, `height_cm`, `weight_kg`, `reach_cm`, `stance` -- all optional.

**UserInfoResponse:** `user_id`, `username`, `display_name`, `user_type`, `level`, `avatar`, `age`, `gender`, `height_cm`, `weight_kg`, `reach_cm`, `stance`.

---

### 3.2 sessions.py -- `/api/sessions`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/current` | Yes | Latest live session. Returns `{active: bool, session: SessionSummary, live_state: dict?}`. Includes buffered WebSocket state if session is active. |
| `GET` | `/history` | Yes | Paginated session history. Query params: `page` (default 1), `page_size` (default 20, max 100), `mode` (optional filter). Returns `SessionHistoryResponse`. |
| `GET` | `/trends` | Yes | Time-series trend analytics. Query param: `range` = `7d|30d|90d|all` (default `30d`). |
| `GET` | `/{session_id}/raw` | Yes | Raw sensor data for a session: CV predictions, IMU strikes, direction timeline, plus summaries from session JSON. |
| `GET` | `/{session_id}` | Yes | Full session detail with config, summary, and events. Returns `SessionDetail`. |

#### Trends Response Shape

```json
{
  "punch_volume": [{"date": "2026-04-01", "value": 150}, ...],
  "reaction_time": [{"date": "...", "value": 320}, ...],
  "defense_rate": [{"date": "...", "value": 0.85}, ...],
  "power": [{"date": "...", "value": 450}, ...],
  "stamina": [{"date": "...", "value": 32.5}, ...],
  "personal_bests": {
    "fastest_reaction_ms": 180,
    "most_punches": 350,
    "best_defense_rate": 0.92,
    "max_power": 520,
    "best_stamina_ppm": 40.2
  },
  "weekly_summary": {
    "sessions": 4,
    "total_punches": 620,
    "avg_score": 72
  },
  "period_comparison": {
    "vs_last_week": "+25%",
    "vs_last_month": "+10%"
  },
  "training_days": [0, 2, 4]
}
```

`training_days` is a list of weekday indices (Mon=0 to Sun=6) indicating which days
the user trained in the current week (used for the heat map on the dashboard).

#### Raw Data Response Shape

```json
{
  "cv_predictions": [...],
  "imu_strikes": [...],
  "direction_timeline": [...],
  "cv_prediction_summary": {},
  "imu_strike_summary": {},
  "direction_summary": {},
  "experimental": {}
}
```

#### Models

**SessionSummary:** `session_id`, `mode`, `difficulty`, `started_at`, `ended_at`, `is_complete`, `rounds_completed`, `rounds_total`, `work_time_sec`, `rest_time_sec`.

**SessionDetail:** extends SessionSummary with `config` (dict), `summary` (dict), `events` (list of dicts).

**SessionHistoryResponse:** `sessions` (list), `total` (int), `page` (int), `page_size` (int).

---

### 3.3 gamification.py -- `/api/gamification`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/profile` | Yes | Gamification profile: XP, rank, next rank, streak, weekly goal/progress, personal records. |
| `GET` | `/achievements` | Yes | List all unlocked achievements for the user. |
| `GET` | `/leaderboard/{coaching_session_id}` | Yes | Leaderboard for a coaching session. Aggregates scores from all individual participants. |
| `GET` | `/benchmarks` | Yes | Population percentile rankings by age/gender. Compares user's best metrics against norms. |

#### Rank Progression

| Rank | XP Threshold |
|---|---|
| Novice | 0 |
| Contender | 500 |
| Fighter | 1,500 |
| Warrior | 4,000 |
| Champion | 10,000 |
| Elite | 25,000 |

#### XP Calculation (GamificationEngine)

- **Base:** 50 XP per session.
- **Mode multiplier:** reaction 1.0x, shadow 1.5x, defence 2.0x, power_test 0.8x, stamina_test 1.2x.
- **Round bonus:** 15 XP per round completed.
- **Completion bonus:** 25 XP if session is complete.
- **Difficulty multiplier:** beginner 1.0x, intermediate 1.3x, advanced 1.6x, elite 2.0x.
- **Minimum:** 10 XP per session.

#### Achievement IDs

| ID | Trigger |
|---|---|
| `first_blood` | First session completed |
| `century` | 100+ punches in a session |
| `fury` | 500+ punches in a session |
| `thousand_fists` | 1000+ punches in a session |
| `speed_demon` | Lightning reaction tier |
| `weekly_warrior` | 7-day streak |
| `consistent` | 30-day streak |
| `iron_chin` | 10 total sessions |
| `marathon` | 50 total sessions |
| `centurion` | 100 total sessions |
| `well_rounded` | 3+ different modes played |
| `perfect_round` | 100% accuracy on a complete session |

#### Benchmarks Response Shape

```json
{
  "benchmarks": {
    "reaction_time": {"percentile": 75, ...},
    "punch_rate": {"percentile": 60, ...},
    "power": {"percentile": 82, ...}
  },
  "user_stats": {"avg_reaction_ms": 250, "total_punches": 1200},
  "demographics": {"age": 22, "gender": "male", "height_cm": 180, "weight_kg": 75}
}
```

---

### 3.4 presets.py -- `/api/presets`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | Yes | List all presets for the authenticated user, sorted by favorite then use_count. |
| `POST` | `/` | Yes | Create a new preset. Returns 201 + `PresetResponse`. |
| `PUT` | `/{preset_id}` | Yes | Update preset fields (name, config_json, description, tags). Returns `{"id": ..., "updated": true}`. |
| `DELETE` | `/{preset_id}` | Yes | Soft-delete (archives) a preset by setting `tags="archived"`. Returns `{"id": ..., "archived": true}`. |
| `POST` | `/{preset_id}/favorite` | Yes | Toggle favorite status. Returns `{"id": ..., "is_favorite": bool}`. |

#### Models

**PresetCreate:** `name` (1-128), `preset_type` (max 32), `config_json` (default "{}"), `description` (max 512), `tags`.

**PresetUpdate:** `name`, `config_json`, `description`, `tags` -- all optional.

**PresetResponse:** `id`, `name`, `description`, `preset_type`, `config_json`, `is_favorite`, `tags`, `use_count`.

---

### 3.5 chat.py -- `/api/chat`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/status` | No | Check if the LLM ROS service is reachable. Returns `{ready: bool, source: "ros"|"none", message?: str}`. |
| `POST` | `/message` | Yes | Send a message to the AI coach. Body: `message` (1-2000 chars), `context` (dict). Returns `ChatResponse`. |
| `GET` | `/history` | Yes | Recent chat history. Query: `limit` (default 50, max 200). Returns list of `ChatMessage`. |

#### LLM Integration

The chat endpoint proxies messages to the ROS `GenerateLlm` service running on the
Jetson (`/boxbunny/llm/generate`). A persistent singleton ROS node
(`dashboard_llm_client`) is created on first use to avoid leaking nodes.

The system prompt includes:
- AIBA coaching methodology
- User's name and level
- Last 5 training sessions (mode, difficulty, rounds, punches)
- Instructions to output `[DRILL:...]` tags for actionable suggestions

#### Training Action Cards

The LLM can embed drill suggestions in its response using tags:

```
[DRILL:Jab-Cross Drill|combo=1-2|rounds=2|work=60s|speed=Medium (2s)]
[DRILL:Power Test|type=power_test]
```

These are parsed by `_parse_actions()` and returned as `TrainingAction` objects:
- `label`: Button text (prefixed with "Start: ")
- `type`: "training", "power_test", "reaction_test", "stamina_test"
- `config`: Route, combo sequence, rounds, work time, speed

#### Health Tracking

The status endpoint tracks inference health:
- After a successful inference, `_llm_verified` is set to True.
- After 2+ consecutive failures, `_llm_verified` resets to False.
- If previously verified, the status endpoint skips the live ping and returns ready.
- Otherwise, it sends a real "Say OK" ping to verify the model is loaded.

---

### 3.6 coach.py -- `/api/coach`

All coach endpoints require `user_type == "coach"` (enforced by `_require_coach`).

| Method | Path | Auth | Coach | Description |
|---|---|---|---|---|
| `POST` | `/load-config` | Yes | Yes | Load a preset as active station config. Broadcasts `config_changed` to all coaches via WebSocket. Increments preset use count. |
| `POST` | `/start-station` | Yes | Yes | Start a coaching station. Body: `name`, `preset_id?`, `config`. Broadcasts `session_started` to all individuals. Returns `coaching_session_id`. |
| `POST` | `/end-session` | Yes | Yes | End a coaching session. Body: `coaching_session_id`. Broadcasts `session_completed` to all individuals. |
| `GET` | `/live` | Yes | Yes | Live participant stats from WebSocket state buffer. Returns list of `ParticipantStats` (username, display_name, rounds_completed, score, connected). |
| `GET` | `/sessions` | Yes | Yes | Past coaching sessions (placeholder, returns empty list). |

---

### 3.7 remote.py -- `/api/remote`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/command` | Yes | Send a remote command to the GUI. Body: `action` (start_training, start_preset, open_presets, stop_session, navigate), `config` (dict). Writes to `/tmp/boxbunny_gui_command.json`. |
| `POST` | `/height` | Yes | Control robot height. Body: `action` (up, down, stop). Maps to `manual_up/manual_down/stop`. Writes to both `/tmp/boxbunny_height_cmd.json` and the main command file. |
| `GET` | `/presets` | Yes | Get user's presets formatted for the GUI (converts DB format to GUI format with route, combo, config, difficulty, accent color). Falls back to default presets on error. |

#### GUI Command File Format

```json
{
  "action": "start_preset",
  "config": {...},
  "username": "alex",
  "timestamp": 1712400000.0
}
```

The desktop GUI polls `/tmp/boxbunny_gui_command.json` for incoming commands.

#### Default Presets (Fallback)

When the database query fails, three hardcoded presets are returned:
1. Free Training (120s work, no combo)
2. Jab-Cross Drill (1-2 combo, 2 rounds, 60s work)
3. Power Test

---

### 3.8 export.py -- `/api/export`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/session/{session_id}/csv` | Yes | Download CSV for a single session. Includes session metadata row + event rows with JSON data. |
| `GET` | `/session/{session_id}/pdf` | Yes | Download an HTML report for a session (printable as PDF). Includes summary JSON and up to 50 events. |
| `GET` | `/range` | Yes | Export all sessions in a date range as CSV. Query: `start_date` (YYYY-MM-DD), `end_date` (YYYY-MM-DD), `mode?`. |

All export endpoints return `StreamingResponse` with appropriate `Content-Disposition`
headers for browser download.

#### CSV Columns

`type`, `session_id`, `mode`, `difficulty`, `started_at`, `ended_at`,
`rounds_completed`, `rounds_total`, `value`, `event_type`

---

## 4. Database Manager

**File:** `src/boxbunny_dashboard/boxbunny_dashboard/db/manager.py`

### Two-Tier SQLite Architecture

The `DatabaseManager` uses two tiers of SQLite databases:

1. **Main database** (`data/boxbunny_main.db`): Shared across all users.
   - `users` table (accounts, password hashes, pattern hashes, profiles)
   - `auth_sessions` table (session tokens with expiry)
   - `guest_sessions` table (guest tokens with claim tracking)
   - `presets` table (user presets with config JSON)

2. **Per-user databases** (`data/users/<username>/boxbunny.db`): One per user.
   - `training_sessions` table (session metadata + config/summary JSON)
   - `session_events` table (timestamped events with JSON data)
   - `power_tests`, `stamina_tests`, `reaction_tests` tables
   - `user_xp` table (XP total, current rank, rank history JSON)
   - `personal_records` table (record type, value, previous value)
   - `streaks` table (current/longest streak, weekly progress)
   - `achievements` table (achievement_id, unlocked_at)

Both tiers use WAL mode and foreign keys enabled.

### Schema Initialization

- Main schema loaded from `data/schema/main_schema.sql` on startup.
- User schema loaded from `data/schema/user_schema.sql` on first user creation.

### Key Methods

#### User Management
- `create_user(username, password, display_name, ...)` -- SHA-256 hash, returns user_id or None
- `verify_password(username, password)` -- Supports SHA-256 and bcrypt
- `set_pattern(user_id, pattern_sequence)` -- SHA-256 hash of dash-joined ints
- `verify_pattern(user_id, pattern_sequence)` -- Supports SHA-256 and bcrypt
- `update_profile(user_id, **kwargs)` -- Allowed fields: display_name, level, age, gender, height_cm, weight_kg, reach_cm, stance, settings_json, proficiency_answers_json, avatar
- `get_user(user_id)`, `get_user_by_username(username)`, `list_users(user_type?)`
- `get_demographic_peers(user_id)` -- Matches gender + age within 5 years

#### Auth Sessions
- `create_auth_session(user_id, device_type, hours=168)` -- Returns token string
- `validate_session_token(token)` -- Returns full user dict or None
- `invalidate_session(token)` -- Sets `is_active = 0`

#### Guest Sessions
- `create_guest_session(ttl_days=7)` -- Returns guest token
- `claim_guest_session(guest_token, user_id)` -- Links guest to user
- `cleanup_expired_guests()` -- Removes expired unclaimed guests

#### Presets
- `get_presets(user_id)` -- Sorted by favorite, then use_count
- `create_preset(user_id, name, preset_type, config_json, description, tags)` -- Returns preset_id
- `update_preset(preset_id, **kwargs)` -- Allowed: name, description, config_json, is_favorite, tags
- `increment_preset_use(preset_id)` -- Bumps use_count

#### Training Sessions (per-user)
- `save_training_session(username, session_data)` -- INSERT OR REPLACE, returns session_id
- `save_session_event(username, session_id, timestamp, event_type, data)` -- Appends event
- `get_session_history(username, limit=50, mode=None)` -- Ordered by started_at DESC
- `get_session_detail(username, session_id)` -- Full session + events
- `get_session_events(username, session_id)` -- Events with parsed data_json

#### Performance Tests (per-user)
- `save_power_test(username, data)` -- peak_force, avg_force, punch_count, results_json
- `save_stamina_test(username, data)` -- duration_sec, total_punches, punches_per_minute, fatigue_index
- `save_reaction_test(username, data)` -- num_trials, avg_reaction_ms, best/worst, tier

#### Gamification (per-user)
- `get_user_xp(username)` -- Returns {total_xp, current_rank} or defaults
- `add_xp(username, xp_amount)` -- Auto-promotes rank, tracks rank history
- `check_personal_record(username, record_type, value)` -- Returns PR dict if broken
- `update_streak(username)` -- Call after each session; handles day transitions
- `unlock_achievement(username, achievement_id)` -- Returns True if newly unlocked
- `get_achievements(username)` -- All unlocked achievements

---

## 5. WebSocket

**File:** `src/boxbunny_dashboard/boxbunny_dashboard/websocket.py`

### Connection Endpoint

`ws://<host>:8080/ws?user_id=<username>&role=<individual|coach>`

### EventType Enum

| Event | Value | Description |
|---|---|---|
| `SESSION_STARTED` | `session_started` | Coaching session began |
| `SESSION_STATS` | `session_stats` | Live stats update during training |
| `SESSION_COMPLETED` | `session_completed` | Session ended |
| `CONFIG_CHANGED` | `config_changed` | Coach loaded a new preset |
| `USER_AUTHENTICATED` | `user_authenticated` | User logged in |

Additional protocol events:
- `ping` / `pong` -- Keepalive (client sends ping, server responds with pong)
- `state_sync` -- Sent to reconnecting clients with buffered state

### ConnectionManager

The `ConnectionManager` class tracks all active WebSocket connections:

**State:**
- `_connections: Dict[str, _ClientConnection]` -- Keyed by `"{user_id}:{ws_id}"`, stores WebSocket reference, user_id, role, and connected_at timestamp.
- `_state_buffer: Dict[str, Dict]` -- Per-user state buffer for reconnection sync.

**Methods:**
- `connect(ws, user_id, role)` -- Accept WebSocket, register client. Immediately sends buffered state via `state_sync` event if available.
- `disconnect(ws, user_id)` -- Remove from active connections.
- `send_to_user(user_id, event, data)` -- Send to all connections for a specific user. Automatically cleans up dead connections.
- `broadcast_to_role(role, event, data)` -- Send to all connections with a given role (e.g., all "individual" users or all "coach" users).
- `update_state(user_id, state)` -- Update the state buffer for reconnection sync.
- `get_connection_count()` -- Total active connections.
- `get_connections_for_role(role)` -- Unique user_ids connected with that role.

### Message Protocol

**Client to Server:**
```json
{"event": "ping", "data": {}}
{"event": "session_stats", "data": {"rounds_completed": 2, "score": 75}}
```

**Server to Client:**
```json
{
  "event": "session_started",
  "data": {"coaching_session_id": "abc123", "name": "Morning Session"},
  "timestamp": "2026-04-06T10:00:00"
}
```

### Reconnection with Buffered State

When a client reconnects:
1. The server accepts the WebSocket and registers it.
2. If `_state_buffer` has an entry for that `user_id`, the server immediately sends
   a `state_sync` event with the buffered state.
3. This ensures the client catches up without missing data during brief disconnects.

### WebSocket Handler Flow

The top-level `websocket_endpoint` function:
1. Extracts `user_id` and `role` from query parameters.
2. Calls `manager.connect(ws, user_id, role)`.
3. Enters an infinite receive loop:
   - Parses incoming JSON messages.
   - Responds to `ping` with `pong`.
   - For known `EventType` values: updates the state buffer and broadcasts to the
     sender's role.
   - For unknown events: responds with `{"error": "unknown_event"}`.
4. On `WebSocketDisconnect` or exception: calls `manager.disconnect(ws, user_id)`.
