# BoxBunny Dashboard -- Frontend Documentation

## 1. Tech Stack

| Technology | Purpose |
|---|---|
| Vue 3 (Composition API) | UI framework, all components use `<script setup>` |
| Pinia | State management (4 stores) |
| Vue Router | Client-side routing with auth guards |
| Tailwind CSS | Utility-first styling with custom `bb-*` design tokens |
| Chart.js + vue-chartjs | Performance trend charts (line, bar, doughnut) |
| Vite | Build tool and dev server |

### Theme

Dark theme throughout. Custom color tokens prefixed `bb-`:
- `bb-bg` -- Background (near-black)
- `bb-surface`, `bb-surface-light`, `bb-surface-lighter` -- Card/surface layers
- `bb-primary` -- Orange accent (#FF6B35)
- `bb-primary-dim` -- Muted orange for backgrounds
- `bb-text`, `bb-text-secondary`, `bb-text-muted` -- Text hierarchy
- `bb-border` -- Subtle borders
- `bb-warning`, `bb-danger` -- Status colors

### Entry Point

**File:** `src/boxbunny_dashboard/frontend/src/main.js`

Creates the Vue app with Pinia and Vue Router, mounts to `#app`.

### App Shell

**File:** `src/boxbunny_dashboard/frontend/src/App.vue`

- Wraps `<router-view>` with `<transition name="page">` for page-level crossfade.
- Shows `<NavBar>` on all pages except login and chat (full-screen views).
- Uses `100dvh` for proper mobile viewport handling.

---

## 2. Router

**File:** `src/boxbunny_dashboard/frontend/src/router.js`

Uses `createWebHistory()` for clean URLs (no hash). Scroll-to-top on navigation.

### Route Table

| Path | Name | View | Auth | Coach | Description |
|---|---|---|---|---|---|
| `/login` | login | LoginView | No | -- | Login/signup screen |
| `/` | dashboard | DashboardView | Yes | -- | Main dashboard |
| `/session/:id` | session-detail | SessionDetailView | Yes | -- | Single session details |
| `/history` | history | HistoryView | Yes | -- | Paginated session history |
| `/performance` | performance | PerformanceView | Yes | -- | Trend charts and analytics |
| `/achievements` | achievements | AchievementsView | Yes | -- | Badges and rank display |
| `/chat` | chat | ChatView | Yes | -- | AI coach chat interface |
| `/training` | training | TrainingView | Yes | -- | Remote training control |
| `/presets` | presets | PresetsView | Yes | -- | Preset CRUD |
| `/settings` | settings | SettingsView | Yes | -- | Profile, security, export |
| `/coach` | coach | CoachView | Yes | Yes | Coach-only dashboard |
| `/:pathMatch(.*)*` | -- | -- | -- | -- | Catch-all redirect to `/` |

### Navigation Guards

`router.beforeEach` enforces:

1. **Auth guard:** Routes with `meta.requiresAuth` redirect to `/login` if not authenticated.
2. **Login redirect:** Authenticated users on `/login` are redirected to `/`.
3. **Coach guard:** Routes with `meta.requiresCoach` redirect to `/` if `user.user_type !== 'coach'`.

All route components use lazy loading via dynamic `import()`.

---

## 3. State Management (Pinia Stores)

### 3.1 Auth Store

**File:** `src/boxbunny_dashboard/frontend/src/stores/auth.js`

**State:**
- `user` (ref, null) -- Current user object (user_id, username, display_name, user_type, level)
- `token` (ref) -- Bearer token, initialised from `localStorage`
- `loading` (ref, false) -- Loading state for auth operations
- `error` (ref, null) -- Last error message

**Computed:**
- `isAuthenticated` -- `!!token`
- `displayName` -- `user.display_name || 'Boxer'`
- `isCoach` -- `user.user_type === 'coach'`

**Actions:**
- `initialize()` -- On store creation, validates existing token via `GET /auth/session`. Clears token if expired.
- `login(username, password)` -- Calls `POST /auth/login`, stores token, sets user, sends `navigate` remote command to GUI.
- `signup(username, password, displayName, level)` -- Calls `POST /auth/signup`, stores token and user.
- `logout()` -- Sends `navigate` remote command (route: auth) to GUI, calls `DELETE /auth/logout`, clears token and user.

### 3.2 Session Store

**File:** `src/boxbunny_dashboard/frontend/src/stores/session.js`

**State:**
- `currentSession` (ref, null) -- Latest session from `/sessions/current`
- `isActive` (ref, false) -- Whether the current session is live
- `liveState` (ref, null) -- WebSocket live state data
- `history` (ref, []) -- Paginated session list
- `historyTotal` (ref, 0) -- Total sessions count
- `historyPage` (ref, 1) -- Current page
- `loading` (ref, false)
- `error` (ref, null)
- `gamification` (ref, null) -- Gamification profile data
- `achievements` (ref, []) -- Unlocked achievements list

**Computed:**
- `totalSessions` -- Alias for historyTotal
- `recentSession` -- First history item, or currentSession as fallback

**Actions:**
- `fetchCurrentSession()` -- `GET /sessions/current`
- `fetchHistory(page, pageSize, mode)` -- `GET /sessions/history`
- `fetchGamification()` -- `GET /gamification/profile`
- `fetchAchievements()` -- `GET /gamification/achievements`

### 3.3 WebSocket Store

**File:** `src/boxbunny_dashboard/frontend/src/stores/websocket.js`

**State:**
- `ws` (ref, null) -- Raw WebSocket instance
- `connected` (ref, false) -- Connection status
- `lastEvent` (ref, null) -- Most recent event received
- `reconnectAttempts` (ref, 0) -- Current reconnect attempt count
- `listeners` (ref, Map) -- Event-name to Set of callbacks

**Actions:**
- `connect(userId, role)` -- Opens WebSocket to `ws://<host>/ws?user_id=...&role=...`. Auto-detects `ws:` vs `wss:` from page protocol.
- `disconnect()` -- Closes WebSocket, clears timers.
- `send(event, data)` -- Sends JSON message if connected.
- `on(event, callback)` -- Registers a listener. Returns an unsubscribe function. Supports wildcard `'*'` listeners.

**Reconnection:**
- Exponential backoff: `min(1000 * 2^attempts, 30000)` ms.
- Max 10 reconnect attempts.
- Resets on successful connection.

**Keepalive:**
- Sends `ping` every 30 seconds while connected.

**Message Dispatch:**
- Parses incoming JSON, dispatches to listeners by event name.
- Also dispatches to `'*'` wildcard listeners.

### 3.4 Chat Store

**File:** `src/boxbunny_dashboard/frontend/src/stores/chat.js`

**State:**
- `messages` (ref, []) -- Array of chat messages `{role, content, timestamp, suggestions?, actions?}`
- `loaded` (ref, false) -- Whether history has been loaded
- `sending` (ref, false) -- Waiting for LLM response
- `streaming` (ref, false) -- Word-by-word reveal in progress

**Actions:**
- `loadHistory()` -- Fetches chat history from `GET /chat/history?limit=50`. Only runs once.
- `sendMessage(text)` -- Adds user message to local array, calls `POST /chat/message`, then reveals the assistant reply word-by-word with 20ms delay between words. Extracts `actions` from the response for training action cards.
- `clearMessages()` -- Resets messages and loaded flag.

---

## 4. API Client

**File:** `src/boxbunny_dashboard/frontend/src/api/client.js`

### Architecture

Fetch-based HTTP client with:
- **Base URL:** `/api` (same-origin, proxied in dev)
- **Auto Bearer injection:** Reads token from `localStorage` key `bb_token`, attaches as `Authorization: Bearer <token>` header.
- **30-second timeout** via `AbortController` (configurable per-call).
- **204 handling:** Returns null for No Content responses.
- **Non-JSON handling:** Returns raw Response for file downloads (CSV, PDF).
- **Error handling:** Throws `ApiError(status, message, data)` for non-OK responses.

### Exported Functions

#### Auth
| Function | Method | Endpoint |
|---|---|---|
| `listUsers()` | GET | `/auth/users` |
| `login(username, password)` | POST | `/auth/login` |
| `signup(username, password, displayName, level)` | POST | `/auth/signup` |
| `patternLogin(username, pattern)` | POST | `/auth/pattern-login` |
| `getSession()` | GET | `/auth/session` |
| `logout()` | DELETE | `/auth/logout` |
| `updateProfile(updates)` | PUT | `/auth/profile` |
| `setPattern(userId, pattern)` | POST | `/auth/set-pattern` |

#### Sessions
| Function | Method | Endpoint |
|---|---|---|
| `getCurrentSession()` | GET | `/sessions/current` |
| `getSessionHistory(page, pageSize, mode)` | GET | `/sessions/history?...` |
| `getSessionDetail(sessionId)` | GET | `/sessions/{sessionId}` |
| `getSessionRawData(sessionId)` | GET | `/sessions/{sessionId}/raw` |

#### Gamification
| Function | Method | Endpoint |
|---|---|---|
| `getGamificationProfile()` | GET | `/gamification/profile` |
| `getAchievements()` | GET | `/gamification/achievements` |
| `getLeaderboard(coachingSessionId)` | GET | `/gamification/leaderboard/{id}` |
| `getBenchmarks()` | GET | `/gamification/benchmarks` |

#### Trends
| Function | Method | Endpoint |
|---|---|---|
| `getSessionTrends(range)` | GET | `/sessions/trends?range=...` |
| `getUserProfile()` | GET | `/auth/session` |

#### Presets
| Function | Method | Endpoint |
|---|---|---|
| `getPresets()` | GET | `/presets/` |
| `createPreset(preset)` | POST | `/presets/` |
| `updatePreset(presetId, updates)` | PUT | `/presets/{presetId}` |
| `deletePreset(presetId)` | DELETE | `/presets/{presetId}` |
| `togglePresetFavorite(presetId)` | POST | `/presets/{presetId}/favorite` |

#### Chat
| Function | Method | Endpoint |
|---|---|---|
| `getChatStatus()` | GET | `/chat/status` |
| `sendChatMessage(message, context)` | POST | `/chat/message` |
| `getChatHistory(limit)` | GET | `/chat/history?limit=...` |

#### Coach
| Function | Method | Endpoint |
|---|---|---|
| `loadCoachConfig(presetId)` | POST | `/coach/load-config` |
| `startStation(name, presetId, config)` | POST | `/coach/start-station` |
| `endCoachSession(coachingSessionId)` | POST | `/coach/end-session` |
| `getLiveParticipants()` | GET | `/coach/live` |
| `getCoachingSessions()` | GET | `/coach/sessions` |

#### Export
| Function | Method | Endpoint |
|---|---|---|
| `exportSessionCSV(sessionId)` | GET | `/export/session/{id}/csv` |
| `exportSessionPDF(sessionId)` | GET | `/export/session/{id}/pdf` |
| `exportDateRange(startDate, endDate, mode)` | GET | `/export/range?...` |

#### Remote GUI Control
| Function | Method | Endpoint |
|---|---|---|
| `sendRemoteCommand(action, config)` | POST | `/remote/command` |
| `sendHeightCommand(action)` | POST | `/remote/height` |
| `getRemotePresets()` | GET | `/remote/presets` |

#### System
| Function | Method | Endpoint |
|---|---|---|
| `healthCheck()` | GET | `/health` |

---

## 5. Views

### 5.1 LoginView

**File:** `src/boxbunny_dashboard/frontend/src/views/LoginView.vue`

Three-step flow:

1. **Auth step:** Toggle between Login and Sign Up.
   - **Login:** Username input with account dropdown (fetched from `GET /auth/users`),
     toggle between password and pattern lock authentication.
   - **Sign Up:** Display name, username, security method toggle (pattern lock or
     password). Pattern lock uses the `PatternLock` component. On success, sets a
     random password internally if pattern-only, then saves the pattern via
     `POST /auth/set-pattern`.

2. **Survey step:** 6-question proficiency assessment (boxing experience, punch
   knowledge, combo ability, sparring experience, fitness level, equipment use).
   Animated slide transitions between questions. Scores answers to suggest a level.

3. **Result step:** Shows suggested level (beginner/intermediate/advanced) with
   description. User can override. Saves level and proficiency answers via
   `PUT /auth/profile`, then navigates to dashboard.

### 5.2 DashboardView

**File:** `src/boxbunny_dashboard/frontend/src/views/DashboardView.vue`

The main home screen. Loads multiple data sources in parallel on mount:

- Session history (last 5), gamification profile, current session
- User profile, benchmarks, trends (30d), remote presets (non-blocking)
- Connects WebSocket with user's username and role

**Sections displayed:**
1. **Header** -- Welcome message, streak display, rank badge
2. **User Profile Card** -- Avatar/initials, display name, demographic info (age/gender/level/stance), height/weight/reach stats
3. **XP Progress Bar** -- Current rank, XP, progress to next rank
4. **Weekly Goal + Streak** -- Goal progress bar, streak flame display
5. **Weekly Training Heat Map** -- Mon-Sun grid showing trained days (from `training_days` in trends), session/punch counts
6. **Quick Stats** -- 2x2 grid of StatCards (total sessions, total punches, best defense %, best reaction ms) with week-over-week trend arrows
7. **Compared to Peers** -- Percentile bars from benchmarks (reaction time, punch rate, power, defense) with tier labels (Elite/Above Average/etc.)
8. **Recent Session** -- SessionCard linking to detail view
9. **AI Coach Says** -- Context-aware tip that changes based on streak, weekly goal, and day of year
10. **Quick Actions** -- 3-button grid (Achievements, Presets, Coach Mode or AI Coach)
11. **Start on Robot** -- Horizontal scroll of remote presets; tapping sends `start_preset` command to GUI

### 5.3 HistoryView

**File:** `src/boxbunny_dashboard/frontend/src/views/HistoryView.vue`

Paginated session history with mode filter tabs:
- All, Training, Sparring, Free, Performance
- Each session rendered as a `SessionCard` (links to detail)
- "Load More" pagination button
- Auto-refreshes when filter tab changes

### 5.4 SessionDetailView

**File:** `src/boxbunny_dashboard/frontend/src/views/SessionDetailView.vue`

Full detail for a single session. Fetches both `/sessions/{id}` and `/sessions/{id}/raw`.

Displays:
- Session metadata (mode, difficulty, date, duration, rounds)
- Summary statistics from session JSON
- Punch distribution charts
- CV predictions, IMU strike data, direction timeline
- Export buttons (CSV, PDF/HTML)

### 5.5 ChatView

**File:** `src/boxbunny_dashboard/frontend/src/views/ChatView.vue`

Full-screen chat interface (no NavBar). Features:

- **Header:** AI avatar, online/offline status indicator (polls `/chat/status` every 5s)
- **Context banner:** Toggle to explain what the AI knows about the user
- **Quick action chips:** Pre-built prompts ("Analyze my last session", "Suggest a drill", etc.)
- **Message bubbles:** User messages in orange (right-aligned), assistant in surface color (left-aligned)
- **Training action cards:** Rendered inline below assistant messages when `actions` are present. Tapping sends remote command to GUI to load the drill.
- **Follow-up suggestions:** Contextual follow-up buttons after assistant messages (e.g., "How many rounds?", "Make it harder")
- **Typing indicator:** Animated dots while waiting for LLM response
- **Word-by-word streaming:** Assistant replies reveal word-by-word with 20ms delay
- **Input:** Text input with 2000-char limit, disabled when LLM is offline or processing

### 5.6 PerformanceView

**File:** `src/boxbunny_dashboard/frontend/src/views/PerformanceView.vue`

Analytics dashboard with trend charts. Features:

- **Date range selector:** 7D, 30D, 90D, All -- fetches from `/sessions/trends`
- **Summary cards:** Sessions count, total punches, average score with period comparisons
- **Chart tabs:** Volume (punches), Reaction (ms), Power, Defense (%), Stamina (PPM)
- **Chart rendering:** Line charts via PunchChart component (Chart.js)
- **Personal Bests section:** Fastest reaction, most punches, best defense rate, max power, best punch rate
- **Population Comparison:** Percentile bars from benchmarks endpoint with quartile markers

### 5.7 AchievementsView

**File:** `src/boxbunny_dashboard/frontend/src/views/AchievementsView.vue`

Displays:
- **Rank section:** Large RankBadge with XP progress bar showing progress to next rank
- **Streak section:** Centered StreakDisplay
- **Achievement grid:** 3-column grid of all 12 achievement badges. Unlocked badges show icon + unlock date. Locked badges show "???" with reduced opacity.
- **Progress summary:** "X / 12 unlocked" with progress bar

Achievement IDs tracked: `first_blood`, `century`, `fury`, `thousand_fists`, `speed_demon`, `weekly_warrior`, `consistent`, `iron_chin`, `marathon`, `centurion`, `well_rounded`, `perfect_round`.

### 5.8 PresetsView

**File:** `src/boxbunny_dashboard/frontend/src/views/PresetsView.vue`

CRUD interface for training presets:
- **Preset list:** Sorted by favorite then default. Each card shows type badge, use count, name, description, favorite toggle (star), start-on-robot button (play), delete button (trash).
- **Create modal:** Bottom sheet with fields for name, type (training/sparring/performance/free/circuit), description, and training config (rounds, work time, rest time, speed, combo sequence, difficulty). Difficulty options are gated by user level.
- **Actions:** Favorite toggle via `POST /presets/{id}/favorite`, delete via `DELETE /presets/{id}`, start on robot via remote command.

### 5.9 SettingsView

**File:** `src/boxbunny_dashboard/frontend/src/views/SettingsView.vue`

Profile and settings page with sections:
1. **Profile** -- Avatar picker (8 avatars + initials option), display name editing. Avatar saved to DB via `PUT /auth/profile`.
2. **Weekly Training Goal** -- Increment/decrement (1-7 sessions/week).
3. **Robot Height** -- Press-and-hold UP/DOWN buttons that send `POST /remote/height` at 10Hz while held.
4. **Security** -- Toggle between password change and pattern lock setup. Pattern uses the PatternLock component, saved via `POST /auth/set-pattern`.
5. **Data Export** -- Date range picker, downloads CSV via `/export/range`.
6. **Navigation links** -- Achievements, Presets, Coach Dashboard (coach only).
7. **About** -- Version 1.0.0.
8. **Logout** -- Disconnects WebSocket, calls logout, redirects to login.

### 5.10 CoachView

**File:** `src/boxbunny_dashboard/frontend/src/views/CoachView.vue`

Coach-only dashboard (guarded by `requiresCoach` route meta):
1. **Connection status** -- WebSocket connected/disconnected indicator, participant count.
2. **Station Control** -- Session name input, optional preset selector, Start/End buttons. Starting a station calls `POST /coach/start-station` and optionally `POST /coach/load-config`.
3. **Live Participants** -- Polled every 5 seconds from `GET /coach/live`. Shows username, display name, connection dot, score, rounds completed. Updates in real-time via WebSocket `session_stats` listener.
4. **Past Sessions** -- Lists previous coaching sessions from `GET /coach/sessions`.

Connects WebSocket with role `"coach"` on mount.

### 5.11 TrainingView

**File:** `src/boxbunny_dashboard/frontend/src/views/TrainingView.vue`

Remote control page for starting training on the robot from the phone:
1. **Quick Start** -- Grid of presets fetched from `GET /remote/presets`. Tapping sends `start_preset` remote command.
2. **Remote Control** -- Navigation buttons: Return Home, Techniques, Sparring, Performance, Quick Start (presets). Each sends a `navigate` or `open_presets` remote command.
3. **Robot Height** -- Opens a modal with press-and-hold UP/DOWN buttons (same 10Hz `POST /remote/height` pattern as SettingsView).
4. **Status feedback** -- Shows success/error messages for 3 seconds after each command.

---

## 6. Components

### 6.1 NavBar

**File:** `src/boxbunny_dashboard/frontend/src/components/NavBar.vue`

Fixed bottom navigation bar with 5 tabs:
- Home (`/`), Train (`/training`), Stats (`/performance`), Coach (`/chat`), Profile (`/settings`)
- Active tab has orange dot indicator and scaled-up icon
- Frosted glass background (`backdrop-filter: blur(20px)`) with 92% opacity black
- Respects `safe-area-inset-bottom` for notched phones
- Hidden on login and chat views (controlled by App.vue)

### 6.2 SessionCard

**File:** `src/boxbunny_dashboard/frontend/src/components/SessionCard.vue`

Clickable card linking to `/session/{session_id}`. Displays:
- **Mode badge** -- Color-coded: reaction (green), shadow (purple), defence (warning), power_test (danger), stamina_test (blue), training (neutral)
- **Difficulty badge** -- Neutral colored
- **Date** -- "Today", "Yesterday", "X days ago", or "Mon DD" format
- **Rounds** -- "X/Y rounds" with duration
- **Grade** -- S/A/B/C/D based on completion ratio (95%/80%/60%/40% thresholds), or "in progress" badge
- Staggered fade-in animation via `delay` prop

### 6.3 PunchChart

**File:** `src/boxbunny_dashboard/frontend/src/components/PunchChart.vue`

Chart.js wrapper supporting bar, line, and doughnut chart types.

**Props:** `title`, `type` ("bar"|"line"|"doughnut"), `labels`, `datasets`, `height`.

**Features:**
- Dark-themed tooltips (black background, rounded corners)
- No legend display
- Line charts: tension 0.4 (smooth curves), point radius 3, fill support
- Bar charts: horizontal axis, border radius 6
- Doughnut charts: 70% cutout
- Shows "No data yet" overlay when datasets are empty

### 6.4 StatCard

**File:** `src/boxbunny_dashboard/frontend/src/components/StatCard.vue`

Single statistic display card.

**Props:** `label`, `value` (number/string), `unit`, `icon` (single character), `subtitle`, `change` (percentage, null to hide), `color` ("green"|"warning"|"danger"|"neutral"), `delay`.

Displays:
- Label in muted uppercase text
- Icon badge in color-coded rounded square
- Large bold value with optional unit
- Optional trend indicator: "+X% vs last week" (green) or "-X% vs last week" (red)
- Staggered animation via delay

### 6.5 RankBadge

**File:** `src/boxbunny_dashboard/frontend/src/components/RankBadge.vue`

Displays a user's rank as a colored badge.

**Props:** `rank`, `xp`, `size` ("sm"|"md"|"lg"), `showLabel`, `showXp`.

**Rank icons and colors:**
| Rank | Icon | Color |
|---|---|---|
| Novice | N | Gray |
| Contender | C | Blue |
| Fighter | F | Orange (primary) |
| Warrior | W | Purple |
| Champion | CH | Yellow (warning) |
| Elite | E | Red (danger) |

### 6.6 StreakDisplay

**File:** `src/boxbunny_dashboard/frontend/src/components/StreakDisplay.vue`

Training streak indicator.

**Props:** `streak` (int), `longest` (int), `showLabel` (bool).

Shows a fire emoji with streak count badge (or snowflake if streak is 0).
Optionally shows "X-day streak" and "Best: Y days" labels.

### 6.7 AchievementBadge

**File:** `src/boxbunny_dashboard/frontend/src/components/AchievementBadge.vue`

Single achievement display tile.

**Props:** `achievementId`, `unlocked` (bool), `unlockedAt` (ISO string).

When unlocked: shows SVG icon from `/achievements/{id}.svg` with colored background and
unlock date. When locked: shows "?" with 40% opacity and "???" name.

**Achievement metadata (12 badges):**
| ID | Name | Background |
|---|---|---|
| first_blood | First Blood | Primary dim |
| century | Century | Blue |
| fury | Fury | Danger dim |
| thousand_fists | 1000 Fists | Purple |
| speed_demon | Speed Demon | Yellow |
| weekly_warrior | Weekly Warrior | Warning dim |
| consistent | Consistent | Primary dim |
| iron_chin | Iron Chin | Gray |
| marathon | Marathon | Blue |
| centurion | Centurion | Warning dim |
| well_rounded | Well Rounded | Purple |
| perfect_round | Perfect Round | Primary dim |

### 6.8 PatternLock

**File:** `src/boxbunny_dashboard/frontend/src/components/PatternLock.vue`

9-dot pattern lock input for authentication.

**Props:** `minDots` (default 4), `size` (default 240px), `error` (bool, turns dots red).

**Emits:** `update:pattern` (on every change), `complete` (on pointer up if >= minDots).

**Exposes:** `reset()` method for programmatic clearing.

**Features:**
- 3x3 grid of circular dots
- SVG line segments connecting selected dots in order
- Active line from last dot to current finger position while drawing
- Hit detection with 34px radius per dot
- Pointer capture for smooth mobile interaction
- Status text: "Connect at least 4 dots" / "X / 4+ dots" / "X dots selected" / "Try again" (error)
- Reset button appears after completion

---

## 7. Real-Time Updates

### WebSocket Integration

The WebSocket store (`stores/websocket.js`) is the central hub for real-time data.

**Connection lifecycle:**
1. DashboardView connects on mount: `wsStore.connect(auth.user.username, auth.user.user_type)`
2. CoachView connects with role `"coach"`: `wsStore.connect(auth.user.username, 'coach')`
3. SettingsView disconnects on logout: `wsStore.disconnect()`

**Event listeners:**
- CoachView subscribes to `session_stats` events to update participant scores in real-time.
- Any component can subscribe via `wsStore.on(eventName, callback)`, which returns an unsubscribe function for cleanup in `onUnmounted`.

**Reconnection:**
- Automatic exponential backoff (1s, 2s, 4s, ..., up to 30s max).
- Max 10 attempts before giving up.
- On reconnect, the server sends buffered state via `state_sync` event.

**Keepalive:**
- Client sends `ping` every 30 seconds.
- Server responds with `pong`.

### Live Session Data Flow

1. The robot publishes training data (punch counts, scores, round progress) to ROS topics.
2. The GUI or a bridge node sends this data to the dashboard WebSocket as `session_stats` events.
3. The `ConnectionManager` buffers the latest state per user and broadcasts to relevant role connections.
4. Frontend components react via Pinia store reactivity or direct WebSocket listeners.
5. On reconnect, the client receives the full buffered state immediately.

### Chat Polling

The ChatView polls LLM status every 5 seconds via `GET /chat/status` to detect
if the AI coach goes offline or comes back online, updating the status indicator
in the chat header.
