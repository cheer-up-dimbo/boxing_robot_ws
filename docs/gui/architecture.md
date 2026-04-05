# BoxBunny GUI -- Application Architecture

Comprehensive reference for the BoxBunny touchscreen GUI, a PySide6 application
designed for a 7-inch 1024x600 display mounted on the Jetson Orin NX.

---

## 1. Application Structure

### Entry Point

The application is launched via `boxbunny_gui.app:main`, which creates a
`BoxBunnyApp` instance and enters the Qt event loop.

**File:** `src/boxbunny_gui/boxbunny_gui/app.py`

### BoxBunnyApp Class

`BoxBunnyApp` is the top-level owner of every subsystem. It follows **constructor
injection with no singletons** -- every dependency is wired explicitly in the
constructor.

#### Initialization Sequence

1. **Logging** -- `logging.basicConfig` with `HH:MM:SS [module] LEVEL: message` format.
2. **QApplication** -- Created with `setApplicationName("BoxBunny")`.
3. **Font loading** -- Loads `InterVariable.ttf` and `InterVariable-Italic.ttf` from `assets/fonts/` via `QFontDatabase.addApplicationFont`.
4. **Global stylesheet** -- Applies `GLOBAL_STYLESHEET` from `theme.py` to the entire application.
5. **Main window** -- `QMainWindow` fixed at 1024x600, titled "BoxBunny".
6. **Stacked widget + QGraphicsView** -- A `QStackedWidget` is embedded inside a `QGraphicsScene`/`QGraphicsView` pair to enable runtime scaling for fullscreen mode (F11). The view has antialiasing and smooth pixmap transforms enabled.
7. **Subsystems** -- Created in order:
   - `GuiBridge` -- ROS 2 bridge (background thread).
   - `PageRouter` -- String-based page navigation with history.
   - `SoundManager` -- Preloaded WAV effects with priority system.
   - `ImuNavHandler` -- IMU pad-to-signal translator.
8. **Keyboard nav filter** -- `KeyboardNavFilter` installed on the window for desktop development (arrow keys, Enter, Escape).
9. **Hotkey filter** -- F11 toggles fullscreen, F12 toggles debug panel, Escape exits fullscreen.
10. **DevOverlay** -- Developer mode overlay positioned at bottom-right, initially hidden.
11. **DebugDetectionPanel** -- Full-page CV debug panel added to the stack, toggled via F12.
12. **PresetOverlay** -- Quick-launch overlay for preset drills, activated via head-pad IMU or remote command.
13. **Signal wiring** -- `_connect_signals()` connects bridge signals to handlers.
14. **Page registration** -- `_register_pages()` imports and instantiates all 24 page classes with dependency injection.
15. **ROS bridge start** -- `self._bridge.start()` launches the background ROS thread.
16. **Remote command polling** -- A 100ms `QTimer` polls `/tmp` JSON files for phone dashboard commands.

#### Dependency Injection

Every page receives its dependencies through its constructor. The `deps` dict passed to page factories contains:

| Key | Type | Purpose |
|-----|------|---------|
| `bridge` | `GuiBridge` | ROS 2 communication |
| `router` | `PageRouter` | Page navigation |
| `sound` | `SoundManager` | Sound effects |
| `imu_nav` | `ImuNavHandler` | IMU navigation signals |
| `dev_overlay` | `DevOverlay` | Developer mode widget |
| `preset_overlay` | `PresetOverlay` | Quick-launch overlay |

The loader uses `inspect.signature` to only pass parameters that each page's
constructor actually accepts, preventing `TypeError` on unused kwargs.

#### Fullscreen Scaling

Toggled via F11. The `QGraphicsView` calculates a uniform scale factor
(`min(screen_w/1024, screen_h/600)`) and applies it via `view.scale()`, then
centers the proxy widget. All UI elements scale proportionally without
layout changes.

---

## 2. Page System

### Overview

The GUI contains **24 pages** organized across **10 directories** (plus 2 overlay
widgets that behave like pages). All pages live under
`src/boxbunny_gui/boxbunny_gui/pages/`.

### PageRouter

**File:** `src/boxbunny_gui/boxbunny_gui/nav/router.py`

The `PageRouter` manages navigation inside the `QStackedWidget`.

**Key features:**

- **String-based routes** -- Pages are registered by name (e.g., `"home"`, `"training_session"`).
- **History stack** -- `navigate()` pushes the current page onto a `List[str]` history. `back()` pops and returns. `replace()` navigates without pushing.
- **Lifecycle hooks** -- Pages may implement the `Routable` protocol:
  - `on_enter(**kwargs)` -- Called when the page becomes visible. Receives navigation kwargs (username, config, combo, etc.).
  - `on_leave()` -- Called when navigating away. Used for cleanup (stopping timers, disconnecting signals).
- **Page kwargs storage** -- `_page_kwargs` dict stores the kwargs for each page so they can be restored on `back()`.
- **Signal** -- `page_changed(str)` emitted on every navigation.

#### Navigation Flow

```
navigate("training_session", username="alex", config={...})
  -> current page.on_leave()
  -> push current to history
  -> set new page as current in QStackedWidget
  -> new page.on_enter(username="alex", config={...})
  -> emit page_changed("training_session")
```

### Complete Page Registry

#### Auth Pages (`pages/auth/`)

| Route Name | File | Class | Purpose |
|------------|------|-------|---------|
| `auth` | `startup_page.py` | `StartupPage` | Landing screen with Log In / Sign Up / Guest buttons and QR code for phone dashboard |
| `account_picker` | `account_picker_page.py` | `AccountPickerPage` | Grid of user account cards with search-as-you-type filtering |
| `pattern_lock` | `pattern_lock_page.py` | `PatternLockPage` | 3x3 Android-style pattern entry for user authentication |
| `signup` | `signup_page.py` | `SignupPage` | New account creation form (username, display name, password, pattern) |
| `guest_assessment` | `guest_assessment_page.py` | `GuestAssessmentPage` | Quick skill-level assessment for guest users before training |

#### Home Pages (`pages/home/`)

| Route Name | File | Class | Purpose |
|------------|------|-------|---------|
| `home` | `home_individual.py` | `HomeIndividualPage` | Main dashboard for logged-in users -- training modes, recent sessions, presets |
| `home_guest` | `home_guest.py` | `HomeGuestPage` | Simplified home for guest users with limited mode access |
| `home_coach` | `home_coach.py` | `HomeCoachPage` | Coach dashboard with station management and multi-user overview |

#### Training Pages (`pages/training/`)

| Route Name | File | Class | Purpose |
|------------|------|-------|---------|
| `training_select` | `combo_select_page.py` | `ComboSelectPage` | Browse and select from the combo library (categorized by difficulty) |
| `training_config` | `training_config_page.py` | `TrainingConfigPage` | Configure drill parameters: rounds, work/rest time, speed, difficulty |
| `training_session` | `training_session_page.py` | `TrainingSessionPage` | Live training HUD with timer, combo display, punch counter, coach tips |
| `training_rest` | `training_rest_page.py` | `TrainingRestPage` | Rest interval screen between rounds with countdown and round progress |
| `training_results` | `training_results_page.py` | `TrainingResultsPage` | Post-session summary with stats, accuracy breakdown, AI coaching feedback |
| `self_select` | `self_select_page.py` | `SelfSelectPage` | Custom combo builder for self-directed training |

#### Sparring Pages (`pages/sparring/`)

| Route Name | File | Class | Purpose |
|------------|------|-------|---------|
| `sparring_select` | `sparring_config_page.py` | `SparringConfigPage` | Configure sparring session parameters (robot aggression, defense mode) |
| `sparring_session` | `sparring_session_page.py` | `SparringSessionPage` | Live sparring HUD -- robot throws punches, user defends and counters |
| `sparring_results` | `sparring_results_page.py` | `SparringResultsPage` | Post-sparring summary with defense stats and reaction times |

#### Performance Pages (`pages/performance/`)

| Route Name | File | Class | Purpose |
|------------|------|-------|---------|
| `performance` | `performance_menu_page.py` | `PerformanceMenuPage` | Menu for selecting performance test type |
| `power_test` | `power_test_page.py` | `PowerTestPage` | Measures maximum punch force via IMU accelerometer data |
| `stamina_test` | `stamina_test_page.py` | `StaminaTestPage` | Timed endurance test tracking punch rate over duration |
| `reaction_test` | `reaction_test_page.py` | `ReactionTestPage` | Audio/visual stimulus response time measurement |

#### Other Pages

| Route Name | File | Class | Purpose |
|------------|------|-------|---------|
| `history` | `pages/history/history_page.py` | `HistoryPage` | Scrollable list of past training sessions with mode, duration, and scores |
| `presets` | `pages/presets/presets_page.py` | `PresetsPage` | Manage saved training presets (create, edit, delete, reorder) |
| `coach` | `pages/coach/station_page.py` | `StationPage` | Coach station management -- monitor connected users, assign drills |
| `settings` | `pages/settings/settings_page.py` | `SettingsPage` | App configuration: volume, developer mode, IMU nav toggle, height adjust |

---

## 3. ROS Bridge

**File:** `src/boxbunny_gui/boxbunny_gui/gui_bridge.py`

### Architecture

The `GuiBridge` class provides thread-safe communication between the ROS 2
network and the Qt GUI:

```
ROS 2 network
    |
    v
_RosWorker (QObject, lives in QThread)
    |  -- emits Qt Signals --
    v
GuiBridge (QObject, lives in main thread)
    |  -- forwards Qt Signals --
    v
Page widgets (connect via signal/slot)
```

### Background Thread

- `_RosWorker` is a `QObject` moved to a `QThread` via `moveToThread()`.
- On `QThread.started`, it calls `start_spinning()` which:
  1. Initializes `rclpy` if needed.
  2. Creates a ROS 2 node named `boxbunny_gui`.
  3. Uses a `SingleThreadedExecutor` spinning at 50ms intervals (`spin_once(timeout_sec=0.05)`).
- ROS callbacks emit Qt `Signal` objects, which are automatically queued across thread boundaries.

### Offline Mode

If `rclpy` is not importable (e.g., running outside a ROS environment), the bridge
runs in **offline mode** (`ROS_AVAILABLE = False`). All service calls return
failure responses, and no subscriptions are created.

### Subscriptions (Inbound)

| Signal | ROS Topic Constant | Message Type | Payload |
|--------|--------------------|--------------|---------|
| `punch_confirmed(dict)` | `Topics.PUNCH_CONFIRMED` | `ConfirmedPunch` | punch_type, pad, level, force, cv_confidence, imu_confirmed, cv_confirmed, accel_magnitude |
| `defense_event(dict)` | `Topics.PUNCH_DEFENSE` | `DefenseEvent` | arm, robot_punch_code, struck, defense_type |
| `drill_progress(dict)` | `Topics.DRILL_PROGRESS` | `DrillProgress` | combos_completed, combos_remaining, overall_accuracy, current_streak, best_streak |
| `session_state_changed(str, str)` | `Topics.SESSION_STATE` | `SessionState` | state, mode |
| `coach_tip(str, str)` | `Topics.COACH_TIP` | `CoachTip` | tip_text, tip_type |
| `nav_command(str)` | `Topics.IMU_NAV_EVENT` | `NavCommand` | command (prev/next/enter/back) |
| `imu_status(dict)` | `Topics.IMU_STATUS` | `IMUStatus` | left_pad, centre_pad, right_pad, head_pad, left_arm, right_arm, is_simulator |
| `cv_detection(str, float)` | `Topics.CV_DETECTION` | `PunchDetection` | punch_type, confidence |
| `strike_complete(dict)` | `Topics.ROBOT_STRIKE_COMPLETE` | `std_msgs/String` | JSON-parsed dict from robot_node |
| `debug_info(dict)` | `Topics.CV_DEBUG_INFO` | `std_msgs/String` | JSON-parsed CV debug metadata |

### Publishers (Outbound)

| Method | ROS Topic Constant | Message Type | Fields |
|--------|--------------------|--------------|--------|
| `publish_punch_command(punch_code, speed, source)` | `Topics.ROBOT_COMMAND` | `RobotCommand` | command_type="punch", punch_code, speed, source |
| `publish_height_command(action)` | `Topics.ROBOT_HEIGHT` | `HeightCommand` | action ("manual_up", "manual_down", "stop") |

### Service Clients

| Method | Service Constant | Service Type | Request Fields | Callback Signature |
|--------|-----------------|--------------|----------------|--------------------|
| `call_start_session(mode, difficulty, config_json, username, callback)` | `Services.START_SESSION` | `StartSession` | mode, difficulty, config_json, username | `callback(success: bool, session_id: str, message: str)` |
| `call_end_session(session_id, callback)` | `Services.END_SESSION` | `EndSession` | session_id | `callback(success: bool, summary_json: str, message: str)` |
| `call_generate_llm(prompt, context_json, system_prompt_key, callback)` | `Services.GENERATE_LLM` | `GenerateLlm` | prompt, context_json, system_prompt_key | `callback(success: bool, response: str, generation_time_sec: float)` |

All service calls are asynchronous (`call_async` with `add_done_callback`).

---

## 4. IMU Navigation

**File:** `src/boxbunny_gui/boxbunny_gui/nav/imu_nav_handler.py`

### ImuNavHandler

Translates NavCommand strings from the ROS bridge into Qt signals that pages
consume for hands-free navigation while wearing boxing gloves.

#### Signals

| Signal | Trigger | IMU Pad | Keyboard Fallback |
|--------|---------|---------|-------------------|
| `navigate_prev` | `"prev"` | Left pad | Left arrow |
| `navigate_next` | `"next"` | Right pad | Right arrow |
| `select` | `"enter"` | Centre pad | Enter / Return |
| `go_back` | `"back"` | Head pad | Escape |

#### Session-State-Aware Disabling

Navigation is automatically disabled during active training sessions. The
`on_session_state_changed(state, mode)` callback tracks the current session state.
When `state` is `"countdown"` or `"active"`, the `enabled` property returns `False`
and all nav commands are silently dropped. This prevents accidental page navigation
from punch impacts during a drill.

#### Keyboard Fallback (KeyboardNavFilter)

A `QObject` event filter installed on the main window that intercepts `KeyPress`
events and delegates them to `ImuNavHandler.handle_key()`. This enables full
desktop development without IMU hardware.

### Nav Command Routing in BoxBunnyApp

The `BoxBunnyApp._on_nav_command()` method provides additional routing logic
on top of the base `ImuNavHandler`:

1. **Preset overlay intercept** -- When the preset overlay is visible, all nav
   commands are routed to it (left/right cycles cards, enter confirms, back dismisses).
2. **Head pad on home pages** -- Toggles the preset quick-launch overlay.
3. **Centre pad on config pages** -- Calls `page.imu_start()` if the current page
   implements it, allowing hands-free session start.

---

## 5. Sound System

**File:** `src/boxbunny_gui/boxbunny_gui/sound.py`

### SoundManager

Low-latency WAV playback via `QSoundEffect`. All sounds are preloaded into memory
at startup for instant playback.

#### Priority System

Higher-priority sounds cannot be masked by lower-priority ones. When a sound is
playing, sounds with lower priority are silently dropped.

| Tier | Priority | Examples |
|------|----------|----------|
| `stimulus` | 5 (highest) | Reaction test stimulus cue |
| `bell` | 4 | Round start/end bell |
| `countdown` | 3 | Countdown ticks and go |
| `feedback` | 2 | Hit confirm, combo complete, miss |
| `ui` | 1 (lowest) | Button press, nav tick, error |

Priority resets to 0 when all sounds finish playing (tracked via
`QSoundEffect.playingChanged`).

#### Sound Catalogue

| Name | File | Priority Tier |
|------|------|---------------|
| `stimulus` | `stimulus.wav` | stimulus (5) |
| `bell_start` | `bell_start.wav` | bell (4) |
| `bell_end` | `bell_end.wav` | bell (4) |
| `countdown_tick` | `countdown_tick.wav` | countdown (3) |
| `countdown_go` | `countdown_go.wav` | countdown (3) |
| `hit_confirm` | `hit_confirm.wav` | feedback (2) -- prefix doesn't match, resolves to 0 |
| `combo_complete` | `combo_complete.wav` | feedback (2) -- prefix doesn't match, resolves to 0 |
| `miss` | `miss.wav` | 0 |
| `btn_press` | `btn_press.wav` | 0 |
| `nav_tick` | `nav_tick.wav` | 0 |
| `error` | `error.wav` | 0 |

Note: Priority is resolved by prefix matching against the `PRIORITY_MAP` keys.
Sounds whose names do not start with a known prefix default to priority 0.

#### API

- `play(name)` -- Play a named sound, respecting priority and per-sound toggles.
- `set_volume(0.0..1.0)` -- Master volume control (default 0.8).
- `set_enabled(name, bool)` -- Per-sound enable/disable toggle.
- `stop_all()` -- Stop all playing sounds and reset priority.

---

## 6. Session Tracking

**File:** `src/boxbunny_gui/boxbunny_gui/session_tracker.py`

### SessionTracker

Maintains a list of completed training sessions in memory, ordered newest-first.

#### Behavior by User Type

- **Guest users** -- Sessions stored in memory only; lost on application close.
- **Logged-in users** -- `load_for_user(username)` loads up to 50 sessions from
  the user's SQLite database at `data/users/<username>/boxbunny.db`.

#### Session Record Fields

| Field | Description |
|-------|-------------|
| `date` | `YYYY-MM-DD` format |
| `time` | `HH:MM` format |
| `mode` | Display name (e.g., "Combo Training", "Sparring") |
| `duration` | Duration string (e.g., "3m") |
| `punches` | Total punch count as string |
| `score` | Score or round progress (e.g., "3/5 rounds") |

#### Global Access

A module-level `get_tracker()` function provides a shared `SessionTracker`
instance. `reset_tracker()` clears it (called on logout).

---

## 7. Database Access

**File:** `src/boxbunny_gui/boxbunny_gui/db_helper.py`

### Overview

Lightweight `sqlite3` wrapper that avoids importing `DatabaseManager` (which
requires native libraries that conflict with the conda environment on aarch64).

**Database path:** `boxing_robot_ws/data/boxbunny_main.db`

### Authentication

- **Password hashing** -- Salted SHA-256 with format `sha256:<salt>:<hash>`. Verification
  uses `hmac.compare_digest` for timing-safe comparison.
- **Pattern hashing** -- Pattern lock sequences (list of dot indices 0-8) are joined
  with `-` separators and hashed with the same SHA-256 scheme.
- **Bcrypt fallback** -- `_verify_hash` also supports bcrypt-formatted hashes for
  backward compatibility.

### API Functions

| Function | Purpose |
|----------|---------|
| `list_users() -> List[Dict]` | All users (id, username, display_name, user_type, level) |
| `get_user(user_id) -> Optional[Dict]` | Single user by ID |
| `get_user_by_username(username) -> Optional[Dict]` | Single user by username |
| `verify_password(username, password) -> Optional[Dict]` | Authenticate; returns user dict or None |
| `verify_pattern(user_id, pattern) -> bool` | Verify pattern lock sequence |
| `update_password(username, new_password) -> bool` | Change password |
| `update_pattern(username, pattern) -> bool` | Change pattern lock |

---

## 8. Remote Command Polling

### Mechanism

A `QTimer` fires every 100ms (10Hz) in `BoxBunnyApp._poll_remote_commands()`,
checking three `/tmp` JSON files written by the phone dashboard Flask server.

### Command Files

#### `/tmp/boxbunny_height_cmd.json`
Continuous height adjustment. Read but **not deleted** (the phone sends updates
continuously). Auto-stops if the command timestamp is older than 500ms (phone
stopped sending).

```json
{"action": "manual_up", "timestamp": 1712345678.9}
```

#### `/tmp/boxbunny_gui_login.json`
Phone login notification. **Deleted after reading.** Skipped if a QR popup dialog
is currently active (it handles its own polling).

```json
{"username": "alex"}
```

#### `/tmp/boxbunny_gui_command.json`
Remote actions from the dashboard. **Deleted after reading.** Supported actions:

| Action | Behavior |
|--------|----------|
| `start_preset` | Load preset config into training config page |
| `open_presets` | Toggle the preset overlay |
| `start_training` | Navigate directly to training session |
| `setup_drill` | Navigate to training config (user starts when ready) |
| `navigate` | Navigate to any route by name |

---

## 9. Widget Library

All reusable widgets live in `src/boxbunny_gui/boxbunny_gui/widgets/` and are
re-exported from `widgets/__init__.py`.

### Widget Inventory

| Widget | File | Description |
|--------|------|-------------|
| `BigButton` | `big_button.py` | Touch-friendly button (min 60x60 px) with glow focus, press animation via `QPropertyAnimation`, and optional left-side icon. Built on `QPushButton`. |
| `StatCard` | `stat_card.py` | Compact stat display card (`QFrame`) with colored left accent bar, title/value labels, and optional trend arrow (up/down/neutral). |
| `ComboDisplay` | `combo_display.py` | Horizontal scrollable combo sequence. Each punch shown as a colored badge. Current step is enlarged with glow; completed/missed steps have overlay marks. Uses per-punch-type color palette. |
| `PunchCounter` | `punch_counter.py` | Large animated punch count display. Scale-pulses on increment via `QPropertyAnimation`. Shows count with optional label above. |
| `TimerDisplay` | `timer_display.py` | Countdown timer with custom-painted rounded-rectangle progress bar. Emits `finished` and `tick(int)` signals. Renders time text centered over a gradient progress track. |
| `CoachTipBar` | `coach_tip_bar.py` | Collapsible AI coaching tip bar that slides down from the top of a page. Has a colored left accent bar indicating tip type. Auto-collapses after 10 seconds. |
| `PresetCard` | `preset_card.py` | Clickable dark-surface card showing preset name, mode badge (color-coded), and config summary. Optional favourite star. |
| `PatternLock` | `pattern_lock.py` | Android-style 3x3 dot grid pattern input. Supports both touch drag and keyboard/IMU input. Dots are 22px radius (28px when active) with generous 48px hit area for gloved fingers. Emits `pattern_entered(List[int])`. |
| `AccountPicker` | `account_picker.py` | User selection grid with search-as-you-type `QLineEdit` filter. 2-3 column responsive grid of dark-surface cards showing display name and level badge. |
| `QRWidget` | `qr_widget.py` | QR code renderer for WiFi credentials and dashboard URLs. Uses the `qrcode` library; falls back to a text label if not installed. |
| `PresetOverlay` | `preset_overlay.py` | Full-width overlay triggered by head-pad IMU. Shows horizontal scrolling preset cards with glow selection highlight. Left/right pads cycle, centre confirms, head pad dismisses. Slides in/out with `QPropertyAnimation`. |
| `HoldTooltipCard` | `hold_tooltip.py` | Card button with press-and-hold (400ms) tooltip. Tap navigates normally; hold reveals a slide-up info bar (250ms animation, 100px height). Releasing dismisses without triggering navigation. |
| `DevOverlay` | `dev_overlay.py` | Developer mode overlay showing a visual model of the boxing robot hardware. Pads and arms light up in real-time on IMU impacts and CV predictions. Layout mirrors physical hardware. Toggled via Settings. Flash duration: 400ms. |
| `DebugDetectionPanel` | `debug_panel.py` | Full-page debug panel (toggled via F12) showing CV detection metadata as styled text: punch type, confidence, frame persistence, IMU match status, FPS, and a scrolling punch log. No camera feed to avoid slowing voxelflow inference. |

---

## 10. File Organization

```
src/boxbunny_gui/boxbunny_gui/
    app.py                  # BoxBunnyApp -- main application entry point
    gui_bridge.py           # GuiBridge -- ROS 2 <-> Qt signal bridge
    sound.py                # SoundManager -- WAV playback with priority
    session_tracker.py      # SessionTracker -- in-memory + DB session history
    db_helper.py            # Database access (sqlite3 + SHA-256 hashing)
    theme.py                # Color, Size, font(), all stylesheet factories
    nav/
        router.py           # PageRouter -- string-based routing + history
        imu_nav_handler.py  # ImuNavHandler -- pad/keyboard nav translation
    pages/
        auth/
            startup_page.py
            account_picker_page.py
            pattern_lock_page.py
            signup_page.py
            guest_assessment_page.py
        home/
            home_individual.py
            home_guest.py
            home_coach.py
        training/
            combo_select_page.py
            training_config_page.py
            training_session_page.py
            training_rest_page.py
            training_results_page.py
            self_select_page.py
        sparring/
            sparring_config_page.py
            sparring_session_page.py
            sparring_results_page.py
        performance/
            performance_menu_page.py
            power_test_page.py
            stamina_test_page.py
            reaction_test_page.py
        history/
            history_page.py
        presets/
            presets_page.py
        coach/
            station_page.py
        settings/
            settings_page.py
    widgets/
        big_button.py
        stat_card.py
        combo_display.py
        punch_counter.py
        timer_display.py
        coach_tip_bar.py
        preset_card.py
        pattern_lock.py
        account_picker.py
        qr_widget.py
        preset_overlay.py
        hold_tooltip.py
        dev_overlay.py
        debug_panel.py
    assets/
        fonts/
            InterVariable.ttf
            InterVariable-Italic.ttf
        sounds/
            stimulus.wav
            bell_start.wav
            bell_end.wav
            countdown_tick.wav
            countdown_go.wav
            hit_confirm.wav
            combo_complete.wav
            miss.wav
            btn_press.wav
            nav_tick.wav
            error.wav
```

---

## 11. Key Design Decisions

1. **No singletons** (except `SessionTracker` for convenience) -- all subsystems
   are owned by `BoxBunnyApp` and passed to pages by reference.
2. **Thread safety via Qt signals** -- ROS callbacks happen on the worker thread
   but emit Qt `Signal` objects, which are auto-queued to the main thread.
3. **Graceful offline mode** -- The entire GUI functions without ROS. All service
   calls return failure responses; all subscriptions are skipped.
4. **QGraphicsView scaling** -- The UI is designed for exactly 1024x600 pixels.
   Fullscreen mode scales the entire scene uniformly, avoiding per-widget
   responsive layout logic.
5. **Inspect-based dependency injection** -- The page loader inspects each page
   class constructor signature and only passes matching kwargs, making it safe
   to add new dependencies without breaking existing pages.
6. **Remote command polling** -- Uses simple `/tmp` JSON files instead of WebSocket
   or HTTP for phone dashboard integration, avoiding additional dependencies on
   the Jetson.
