# Session State Machine Reference

> Complete reference for recreating the session state machine diagram — every state, transition, timer, and side effect.

---

## 1. States and Transitions

```
IDLE ──StartSession──> COUNTDOWN ──3s──> ACTIVE ──round timer──> REST ──rest timer──> COUNTDOWN
                                           |                                            |
                                           +──final round──> COMPLETE ──auto 3s──> IDLE |
                                           +──EndSession───> COMPLETE                   |
                                                                                        |
                                                          (loop for multi-round) ───────+
```

| State | Purpose | Entry Trigger | Exit Trigger |
|---|---|---|---|
| **IDLE** | Waiting for session | System startup, or auto-reset 3s after COMPLETE | StartSession service call |
| **COUNTDOWN** | Preparation before round | StartSession, or rest timer expired | Countdown reaches 0 (3s default) |
| **ACTIVE** | Round in progress, all data collected | Countdown expires | Work timer expires, or EndSession call |
| **REST** | Between-round pause | Round completes (not final) | Rest timer expires |
| **COMPLETE** | Session finished, summary published | Final round ends, or EndSession (early stop) | Auto-reset after 3s delay |

---

## 2. SessionState Message

```
string state      # "idle", "countdown", "active", "rest", "complete"
string mode       # "training", "sparring", "free", "power", "stamina", "reaction"
string username   # Current user or "guest"
```

**Publication rate:** 2 Hz heartbeat (all states)

---

## 3. Timer Durations

| Timer | Default | Configurable | Source |
|---|---|---|---|
| Countdown | 3 seconds | `countdown_seconds` param | boxbunny.yaml |
| Work (round) | 180 seconds (3 min) | StartSession config_json | gui.yaml defaults |
| Rest | 60 seconds (1 min) | StartSession config_json | gui.yaml defaults |
| Auto-reset (complete→idle) | 3 seconds | Hardcoded | session_manager.py |
| State publish heartbeat | 2 Hz (0.5s) | Hardcoded | session_manager.py |
| Autosave interval | 10 seconds | `autosave_interval_s` param | boxbunny.yaml |

---

## 4. Round Cycling

**Default:** 3 rounds x 180s work + 60s rest

```
Round 1: COUNTDOWN (3s) → ACTIVE (180s) → REST (60s)
Round 2: COUNTDOWN (3s) → ACTIVE (180s) → REST (60s)
Round 3: COUNTDOWN (3s) → ACTIVE (180s) → COMPLETE (auto-reset 3s)
```

**Key variables:**
- `current_round`: 1-indexed, incremented on each ACTIVE entry
- `total_rounds`: Target (default 3)
- `work_time_s`: Per-round active duration (default 180s)
- `rest_time_s`: Between-round rest (default 60s)

---

## 5. Training Modes

| Mode | Description | Robot Behavior |
|---|---|---|
| training | Combo drill sequences | No robot attacks |
| sparring | AI opponent (Markov-chain styles) | Robot attacks at intervals |
| free | Reactive counter-punches | Robot counters user punches |
| power | Max punch force test | No robot attacks |
| stamina | Extended punch volume/fatigue | No robot attacks |
| reaction | Defense reaction time test | Robot attacks, measure response |

---

## 6. StartSession Service

**Request:**
```
string mode          # Training mode
string difficulty    # beginner, intermediate, advanced
string config_json   # Full session config as JSON
string username      # User or "guest"
```

**Response:**
```
bool success
string session_id    # UUID-based (12 chars)
string message
```

**Config JSON fields:** mode, difficulty, rounds, work_time_sec, rest_time_sec, speed, style, combo_sequence

---

## 7. EndSession Service

**Request:**
```
string session_id
```

**Response:**
```
bool success
string summary_json   # Complete session statistics
string message
```

---

## 8. Side Effects Per State

### IDLE
| Category | Behavior |
|---|---|
| IMU Mode | NAVIGATION (pad taps = GUI navigation) |
| CV | Idle / reduced processing |
| Robot | Disabled |
| GUI | Home/menu pages, preset overlay available |
| Database | No writes |
| Publications | SessionState heartbeat only |

### COUNTDOWN
| Category | Behavior |
|---|---|
| IMU Mode | TRAINING (switches with 200ms grace period) |
| CV | Active (warming up) |
| Robot | Receives RoundControl "start" |
| GUI | Countdown overlay (3... 2... 1...) |
| Height Auto-Adjust | Publishes HeightCommand if user detected (once per countdown, target 15% frame height, 15px deadband) |
| Publications | SessionState, HeightCommand (once) |

### ACTIVE
| Category | Behavior |
|---|---|
| IMU Mode | TRAINING (pad impacts = PunchEvent) |
| CV | Full 30fps processing, publishing PunchDetection |
| Robot | Executes punches (sparring/free mode), tracks strikes |
| GUI | Live session page (punch count, timer, coach tips) |
| Data Collection | ConfirmedPunch, DefenseEvent, UserTracking, CV predictions, IMU strikes, direction changes, robot commands |
| Autosave | Every 10 seconds (logs session state) |
| Publications | SessionState, SessionPunchSummary (at end) |
| Sparring Engine | Active only when mode="sparring" (Markov attacks at difficulty interval) |
| Free Training | Active only when mode="free" (counter-punches on IMU events) |
| Drill Manager | Active only when mode="training" (combo validation) |

### REST
| Category | Behavior |
|---|---|
| IMU Mode | TRAINING (maintained from active) |
| CV | Idle / reduced load |
| Robot | Idle (no attacks) |
| GUI | Rest timer countdown displayed |
| Data Collection | None |
| Publications | SessionState heartbeat |

### COMPLETE
| Category | Behavior |
|---|---|
| IMU Mode | Transitions to NAVIGATION |
| CV | Idle |
| Robot | Disabled |
| GUI | Results page shown (summary stats) |
| Database | Session saved to per-user SQLite DB |
| Summary Published | SessionPunchSummary message (once) |
| Publications | SessionState, SessionPunchSummary |
| Auto-Reset | Timer fires after 3s → return to IDLE |

---

## 9. Node Reactions to Session State

### imu_node
```
countdown/active/rest → IMU mode: TRAINING (pad impacts = PunchEvent)
idle/complete         → IMU mode: NAVIGATION (pad taps = NavCommand)
Transition grace period: 200ms
```

### sparring_engine
```
state="active" AND mode="sparring" → Activate (Markov attack loop at 10Hz)
Any other state/mode              → Deactivate
Attack intervals: easy=2.0s, medium=1.2s, hard=0.7s
Counter-punch probability: easy=0.3, medium=0.5, hard=0.8
Session timeout watchdog: 5 seconds
```

### free_training_engine
```
state="active" AND mode="free" → Activate (reactive counter-punches)
Any other state/mode           → Deactivate
Counter cooldown: 300ms
Pad→Counter mapping: centre→jab/cross, left→L hook/upper, right→R hook/upper, head→jab/cross
```

### punch_processor
```
Subscribes to SessionState for lifecycle awareness
Fuses CV + IMU only during active sessions
Defense windows opened by RobotCommand during active state
```

### drill_manager
```
Activated via StartDrill service (called by session_manager for drill mode)
Validates combo sequences against ConfirmedPunch events
Timeout check: 2 Hz
```

### analytics_node
```
Accumulates stats from ConfirmedPunch and DefenseEvent
Publishes analytics JSON at 5 Hz during active
Resets on new session
```

### llm_node
```
Generates coaching tips every ~18s during active state
Post-session analysis on SessionPunchSummary
Subscribes to ConfirmedPunch and DrillEvent for context
```

---

## 10. Session Summary Statistics

**Published as SessionPunchSummary on COMPLETE:**

| Category | Fields |
|---|---|
| Core | session_id, mode, difficulty, total_punches, rounds_completed, duration_sec, punches_per_minute |
| Punch Analysis | punch_distribution (type→count), force_distribution (type→avg_force), pad_distribution (pad→count), max_power |
| Defense | robot_punches_thrown, robot_punches_landed, defense_rate, defense_breakdown (type→count) |
| Movement | avg_depth, depth_range, lateral_movement, max_lateral_displacement, max_depth_displacement |
| CV Analysis | cv_prediction_summary (type→{events, total_frames, avg_conf}) |
| IMU Analysis | imu_strike_summary (pad→count), imu_strikes_total, imu_confirmation_rate |
| Direction | direction_summary (left/right/centre→time_seconds) |
| Experimental | defense_reactions (list), avg_reaction_time_ms |

---

## 11. Concurrent Session Protection

If StartSession is called while not IDLE:
- Force-resets current session (cancel timers, clear session data)
- Transitions to IDLE
- Then starts new session normally
- Only one active session at a time

---

## 12. Configuration Hierarchy (highest to lowest priority)

1. **StartSession.config_json** — passed per-session
2. **boxbunny.yaml defaults** — training.default_rounds, default_work_time_s, etc.
3. **gui.yaml defaults** — session_defaults.rounds, work_time_sec, etc.
4. **Hardcoded defaults** — total_rounds=3, work_time_s=180, rest_time_s=60

---

## 13. Complete Data Flow (for diagram)

```
StartSession service call (from GUI or Dashboard)
  │
  ▼
IDLE → COUNTDOWN (3s)
  │     - Height auto-adjust (HeightCommand, once)
  │     - IMU switches to TRAINING mode
  │     - RoundControl "start" to robot
  │
  ▼
ACTIVE (work_time_s, default 180s)
  │     - Collects: ConfirmedPunch, DefenseEvent, UserTracking, CV, IMU
  │     - Sparring: robot attacks at difficulty interval
  │     - Free: robot counters user punches
  │     - Drills: combo validation
  │     - LLM: coaching tips every ~18s
  │     - Autosave every 10s
  │
  ├── Not final round ──► REST (rest_time_s, default 60s)
  │                           │     - IMU stays TRAINING
  │                           │     - No data collection
  │                           │     - GUI shows rest countdown
  │                           │
  │                           └──► COUNTDOWN (loop back)
  │
  └── Final round OR EndSession ──► COMPLETE
                                      │     - Publish SessionPunchSummary
                                      │     - Save session to per-user DB
                                      │     - IMU switches to NAVIGATION
                                      │     - GUI shows results page
                                      │
                                      └──► IDLE (auto-reset after 3s)
```
