# BoxBunny Data Layer

This document covers the complete data architecture, database schemas, session summaries, gamification system, population benchmarks, and demo data.

---

## Table of Contents

1. [Two-Tier Architecture](#1-two-tier-architecture)
2. [Main Database](#2-main-database)
3. [Per-User Database](#3-per-user-database)
4. [Session Summary Fields](#4-session-summary-fields)
5. [Gamification System](#5-gamification-system)
6. [Population Benchmarks](#6-population-benchmarks)
7. [Demo Users](#7-demo-users)

---

## 1. Two-Tier Architecture

BoxBunny uses a **two-tier SQLite database architecture**:

- **Main Database** (`data/boxbunny_main.db`) -- Shared data accessible to all users and the system.
- **Per-User Databases** (`data/users/{username}/boxbunny.db`) -- One database per registered user containing all personal training data.

### Rationale

| Concern              | How Two-Tier Solves It                                                 |
|----------------------|------------------------------------------------------------------------|
| **Data Isolation**   | Each user's training data is physically separated. One user's data cannot accidentally leak to or corrupt another's. |
| **Backup/Deletion**  | Backing up or deleting a single user's data is a simple filesystem operation (copy or remove one directory). No complex SQL queries needed. |
| **Contention**       | SQLite has a single-writer lock. By isolating per-user writes to separate database files, concurrent training sessions for different users never contend on the same lock. |
| **Portability**      | A user's entire training history can be exported as a single `.db` file. |

### File Layout

```
data/
  boxbunny_main.db              # Shared main database
  schema/
    main_schema.sql             # Main DB schema definition
    user_schema.sql             # Per-user DB schema definition
  users/
    alex/
      boxbunny.db               # Alex's personal training data
    maria/
      boxbunny.db               # Maria's personal training data
    jake/
      boxbunny.db               # Jake's personal training data
    sarah/
      boxbunny.db               # Sarah's personal training data
  benchmarks/
    population_norms.json       # Population benchmark data
```

---

## 2. Main Database

**File:** `data/boxbunny_main.db`
**Schema:** `data/schema/main_schema.sql`

### Table: `users`

Stores all registered user accounts.

| Column                   | Type    | Constraints / Default                                          | Description                                    |
|--------------------------|---------|----------------------------------------------------------------|------------------------------------------------|
| `id`                     | INTEGER | PRIMARY KEY AUTOINCREMENT                                      | Unique user ID                                 |
| `username`               | TEXT    | UNIQUE NOT NULL                                                | Login username                                 |
| `password_hash`          | TEXT    | NOT NULL                                                       | Bcrypt/hashed password                         |
| `pattern_hash`           | TEXT    |                                                                | Optional pattern-lock hash for quick login     |
| `display_name`           | TEXT    | NOT NULL                                                       | Name shown in UI                               |
| `user_type`              | TEXT    | NOT NULL DEFAULT 'individual', CHECK IN ('individual','coach') | Account type                                   |
| `level`                  | TEXT    | NOT NULL DEFAULT 'beginner', CHECK IN ('beginner','intermediate','advanced') | Self-reported skill level       |
| `age`                    | INTEGER |                                                                | User's age                                     |
| `gender`                 | TEXT    | CHECK IN ('male','female','other', NULL)                       | Gender for benchmark comparisons               |
| `height_cm`              | REAL    |                                                                | Height in centimeters                          |
| `weight_kg`              | REAL    |                                                                | Weight in kilograms                            |
| `reach_cm`               | REAL    |                                                                | Arm reach in centimeters                       |
| `stance`                 | TEXT    | DEFAULT 'orthodox', CHECK IN ('orthodox','southpaw')           | Fighting stance                                |
| `created_at`             | TEXT    | NOT NULL DEFAULT datetime('now')                               | Account creation timestamp                     |
| `last_login`             | TEXT    |                                                                | Most recent login timestamp                    |
| `settings_json`          | TEXT    | NOT NULL DEFAULT '{}'                                          | User preferences as JSON                       |
| `proficiency_answers_json` | TEXT  |                                                                | Onboarding proficiency questionnaire answers   |

**Indexes:** `idx_users_username` (username), `idx_users_user_type` (user_type)

### Table: `auth_sessions`

Tracks active authentication sessions for token-based auth.

| Column          | Type    | Constraints / Default                              | Description                          |
|-----------------|---------|-----------------------------------------------------|--------------------------------------|
| `id`            | INTEGER | PRIMARY KEY AUTOINCREMENT                           | Session record ID                    |
| `user_id`       | INTEGER | FK -> users(id) ON DELETE CASCADE                   | Owning user                          |
| `session_token` | TEXT    | UNIQUE NOT NULL                                     | Bearer token                         |
| `device_type`   | TEXT    | NOT NULL, CHECK IN ('phone','robot')                | Which device initiated the session   |
| `created_at`    | TEXT    | NOT NULL DEFAULT datetime('now')                    | Session creation time                |
| `expires_at`    | TEXT    | NOT NULL                                            | Token expiry time                    |
| `is_active`     | INTEGER | NOT NULL DEFAULT 1                                  | Whether session is still valid       |

**Indexes:** `idx_auth_sessions_token` (session_token), `idx_auth_sessions_user` (user_id)

### Table: `guest_sessions`

Supports guest (unauthenticated) usage that can later be claimed by a registered user.

| Column               | Type    | Constraints / Default                          | Description                              |
|----------------------|---------|------------------------------------------------|------------------------------------------|
| `id`                 | INTEGER | PRIMARY KEY AUTOINCREMENT                      | Guest session record ID                  |
| `guest_session_token`| TEXT    | UNIQUE NOT NULL                                | Temporary guest token                    |
| `created_at`         | TEXT    | NOT NULL DEFAULT datetime('now')               | When the guest session started           |
| `claimed_by_user_id` | INTEGER | FK -> users(id) ON DELETE SET NULL             | User who claimed this guest session      |
| `claimed_at`         | TEXT    |                                                | When the session was claimed             |
| `expires_at`         | TEXT    | NOT NULL                                       | Guest session expiry                     |

**Indexes:** `idx_guest_sessions_token` (guest_session_token)

### Table: `presets`

Stores saved training configuration presets.

| Column        | Type    | Constraints / Default                                                        | Description                        |
|---------------|---------|------------------------------------------------------------------------------|------------------------------------|
| `id`          | INTEGER | PRIMARY KEY AUTOINCREMENT                                                    | Preset ID                          |
| `user_id`     | INTEGER | NOT NULL, FK -> users(id) ON DELETE CASCADE                                  | Owning user                        |
| `name`        | TEXT    | NOT NULL                                                                     | Preset display name                |
| `description` | TEXT    | DEFAULT ''                                                                   | Optional description               |
| `preset_type` | TEXT    | NOT NULL, CHECK IN ('training','sparring','performance','circuit','free')     | What mode this preset configures   |
| `config_json` | TEXT    | NOT NULL DEFAULT '{}'                                                        | Full configuration as JSON         |
| `is_favorite` | INTEGER | NOT NULL DEFAULT 0                                                           | Favorited flag                     |
| `tags`        | TEXT    | DEFAULT ''                                                                   | Comma-separated tags               |
| `created_at`  | TEXT    | NOT NULL DEFAULT datetime('now')                                             | Creation timestamp                 |
| `updated_at`  | TEXT    | NOT NULL DEFAULT datetime('now')                                             | Last modification timestamp        |
| `use_count`   | INTEGER | NOT NULL DEFAULT 0                                                           | How many times this preset was used|

**Indexes:** `idx_presets_user` (user_id)

### Table: `coaching_sessions`

Records group circuit training sessions run by coaches.

| Column                    | Type    | Constraints / Default                              | Description                         |
|---------------------------|---------|-----------------------------------------------------|-------------------------------------|
| `id`                      | INTEGER | PRIMARY KEY AUTOINCREMENT                           | Session ID                          |
| `coach_user_id`           | INTEGER | NOT NULL, FK -> users(id) ON DELETE CASCADE         | Coach who ran the session           |
| `station_config_preset_id`| INTEGER | FK -> presets(id) ON DELETE SET NULL                 | Preset used for configuration       |
| `started_at`              | TEXT    | NOT NULL DEFAULT datetime('now')                    | Session start time                  |
| `ended_at`                | TEXT    |                                                     | Session end time                    |
| `total_participants`      | INTEGER | NOT NULL DEFAULT 0                                  | Number of participants              |
| `notes`                   | TEXT    | DEFAULT ''                                          | Coach notes                         |

### Table: `coaching_participants`

Records individual participant data within a coaching session.

| Column               | Type    | Constraints / Default                                    | Description                          |
|----------------------|---------|----------------------------------------------------------|--------------------------------------|
| `id`                 | INTEGER | PRIMARY KEY AUTOINCREMENT                                | Record ID                            |
| `coaching_session_id`| INTEGER | NOT NULL, FK -> coaching_sessions(id) ON DELETE CASCADE  | Parent coaching session              |
| `participant_number` | INTEGER | NOT NULL                                                 | Order number (1-based)               |
| `participant_name`   | TEXT    | DEFAULT ''                                               | Optional participant name            |
| `session_data_json`  | TEXT    | NOT NULL DEFAULT '{}'                                    | Participant's session data as JSON   |
| `created_at`         | TEXT    | NOT NULL DEFAULT datetime('now')                         | Record creation time                 |

**Indexes:** `idx_coaching_participants_session` (coaching_session_id)

---

## 3. Per-User Database

**File:** `data/users/{username}/boxbunny.db`
**Schema:** `data/schema/user_schema.sql`

Each registered user gets an isolated SQLite database containing all their training history, progress, and gamification data.

### Table: `training_sessions`

The central record for every training session (all modes).

| Column            | Type    | Constraints / Default                | Description                            |
|-------------------|---------|--------------------------------------|----------------------------------------|
| `id`              | INTEGER | PRIMARY KEY AUTOINCREMENT            | Auto-increment row ID                  |
| `session_id`      | TEXT    | UNIQUE NOT NULL                      | UUID for the session                   |
| `mode`            | TEXT    | NOT NULL                             | Training mode (e.g., 'training', 'sparring', 'free', 'power', 'stamina', 'reaction') |
| `difficulty`      | TEXT    | NOT NULL DEFAULT 'beginner'          | Difficulty level                       |
| `started_at`      | TEXT    | NOT NULL DEFAULT datetime('now')     | Session start timestamp                |
| `ended_at`        | TEXT    |                                      | Session end timestamp                  |
| `is_complete`     | INTEGER | NOT NULL DEFAULT 0                   | Whether session completed normally     |
| `rounds_completed`| INTEGER | NOT NULL DEFAULT 0                   | Rounds finished                        |
| `rounds_total`    | INTEGER | NOT NULL DEFAULT 0                   | Rounds configured                      |
| `work_time_sec`   | INTEGER | NOT NULL DEFAULT 180                 | Work period per round (seconds)        |
| `rest_time_sec`   | INTEGER | NOT NULL DEFAULT 60                  | Rest period between rounds (seconds)   |
| `config_json`     | TEXT    | NOT NULL DEFAULT '{}'                | Full session configuration snapshot    |
| `summary_json`    | TEXT    | DEFAULT '{}'                         | Post-session summary (see Section 4)   |

**Indexes:** `idx_training_sessions_id` (session_id), `idx_training_sessions_mode` (mode)

### Table: `session_events`

Time-series event log for every action within a session.

| Column       | Type    | Constraints / Default                                    | Description                          |
|--------------|---------|----------------------------------------------------------|--------------------------------------|
| `id`         | INTEGER | PRIMARY KEY AUTOINCREMENT                                | Event record ID                      |
| `session_id` | TEXT    | NOT NULL, FK -> training_sessions(session_id) ON DELETE CASCADE | Parent session                 |
| `timestamp`  | REAL    | NOT NULL                                                 | Unix timestamp of the event          |
| `event_type` | TEXT    | NOT NULL                                                 | Event category (e.g., 'punch', 'defense', 'round_start', 'round_end') |
| `data_json`  | TEXT    | NOT NULL DEFAULT '{}'                                    | Event payload as JSON                |

**Indexes:** `idx_session_events_session` (session_id), `idx_session_events_type` (event_type)

### Table: `combo_progress`

Tracks mastery progress for each combo drill.

| Column          | Type    | Constraints / Default         | Description                         |
|-----------------|---------|-------------------------------|-------------------------------------|
| `id`            | INTEGER | PRIMARY KEY AUTOINCREMENT     | Row ID                              |
| `combo_id`      | TEXT    | NOT NULL, UNIQUE              | Unique combo identifier             |
| `combo_name`    | TEXT    | NOT NULL                      | Human-readable combo name           |
| `difficulty`    | TEXT    | NOT NULL                      | Combo difficulty tier               |
| `attempts`      | INTEGER | NOT NULL DEFAULT 0            | Total attempts                      |
| `best_accuracy` | REAL    | NOT NULL DEFAULT 0.0          | Best accuracy achieved (0.0-1.0)    |
| `avg_accuracy`  | REAL    | NOT NULL DEFAULT 0.0          | Running average accuracy            |
| `mastered`      | INTEGER | NOT NULL DEFAULT 0            | Mastery flag (0 or 1)              |
| `last_attempted`| TEXT    |                               | Timestamp of last attempt           |

**Indexes:** `idx_combo_progress_combo` (combo_id)

### Table: `power_tests`

Records power test results.

| Column        | Type    | Constraints / Default             | Description                     |
|---------------|---------|-----------------------------------|---------------------------------|
| `id`          | INTEGER | PRIMARY KEY AUTOINCREMENT         | Row ID                          |
| `tested_at`   | TEXT    | NOT NULL DEFAULT datetime('now')  | When the test was taken         |
| `peak_force`  | REAL    | NOT NULL DEFAULT 0.0              | Maximum single-punch force      |
| `avg_force`   | REAL    | NOT NULL DEFAULT 0.0              | Mean force across all punches   |
| `punch_count` | INTEGER | NOT NULL DEFAULT 0                | Total punches in the test       |
| `results_json`| TEXT    | NOT NULL DEFAULT '[]'             | Per-punch force data            |

### Table: `stamina_tests`

Records stamina test results.

| Column              | Type    | Constraints / Default             | Description                          |
|---------------------|---------|-----------------------------------|--------------------------------------|
| `id`                | INTEGER | PRIMARY KEY AUTOINCREMENT         | Row ID                               |
| `tested_at`         | TEXT    | NOT NULL DEFAULT datetime('now')  | When the test was taken              |
| `duration_sec`      | INTEGER | NOT NULL DEFAULT 120              | Test duration in seconds             |
| `total_punches`     | INTEGER | NOT NULL DEFAULT 0                | Raw punch count                      |
| `punches_per_minute`| REAL    | NOT NULL DEFAULT 0.0              | Average punches per minute           |
| `fatigue_index`     | REAL    | NOT NULL DEFAULT 0.0              | Late-round / early-round rate ratio  |
| `results_json`      | TEXT    | NOT NULL DEFAULT '[]'             | Time-series punch rate data          |

### Table: `reaction_tests`

Records reaction test results.

| Column            | Type    | Constraints / Default             | Description                       |
|-------------------|---------|-----------------------------------|-----------------------------------|
| `id`              | INTEGER | PRIMARY KEY AUTOINCREMENT         | Row ID                            |
| `tested_at`       | TEXT    | NOT NULL DEFAULT datetime('now')  | When the test was taken           |
| `num_trials`      | INTEGER | NOT NULL DEFAULT 10               | Number of trials in the test      |
| `avg_reaction_ms` | REAL    | NOT NULL DEFAULT 0.0              | Mean reaction time (ms)           |
| `best_reaction_ms`| REAL    | NOT NULL DEFAULT 0.0              | Fastest trial (ms)                |
| `worst_reaction_ms`| REAL   | NOT NULL DEFAULT 0.0              | Slowest trial (ms)                |
| `tier`            | TEXT    | NOT NULL DEFAULT 'average'        | Result tier (lightning/fast/average/developing) |
| `results_json`    | TEXT    | NOT NULL DEFAULT '[]'             | Per-trial reaction times          |

### Table: `sparring_sessions`

Records detailed sparring session results.

| Column                   | Type    | Constraints / Default                                    | Description                          |
|--------------------------|---------|----------------------------------------------------------|--------------------------------------|
| `id`                     | INTEGER | PRIMARY KEY AUTOINCREMENT                                | Row ID                               |
| `session_id`             | TEXT    | NOT NULL, FK -> training_sessions(session_id) ON DELETE CASCADE | Parent training session        |
| `style`                  | TEXT    | NOT NULL DEFAULT 'boxer'                                 | AI opponent style used               |
| `difficulty`             | TEXT    | NOT NULL DEFAULT 'medium'                                | Difficulty level                     |
| `rounds_completed`       | INTEGER | NOT NULL DEFAULT 0                                       | Rounds finished                      |
| `user_punches`           | INTEGER | NOT NULL DEFAULT 0                                       | User's total punches                 |
| `robot_punches_thrown`   | INTEGER | NOT NULL DEFAULT 0                                       | Robot attacks thrown                  |
| `robot_punches_landed`   | INTEGER | NOT NULL DEFAULT 0                                       | Robot attacks that landed (hit)      |
| `defense_rate`           | REAL    | NOT NULL DEFAULT 0.0                                     | (thrown - landed) / thrown            |
| `punch_distribution_json`| TEXT   | NOT NULL DEFAULT '{}'                                    | Breakdown by punch type              |
| `defense_breakdown_json` | TEXT   | NOT NULL DEFAULT '{}'                                    | Breakdown by defense type            |
| `completed_at`           | TEXT    | NOT NULL DEFAULT datetime('now')                         | When the sparring session ended      |

### Table: `sparring_weakness_profile`

Persistent per-user weakness tracking across sparring sessions.

| Column               | Type    | Constraints / Default             | Description                              |
|----------------------|---------|-----------------------------------|------------------------------------------|
| `id`                 | INTEGER | PRIMARY KEY AUTOINCREMENT         | Row ID                                   |
| `punch_type`         | TEXT    | NOT NULL, UNIQUE                  | Punch type (jab, cross, etc.)            |
| `defense_success_rate`| REAL   | NOT NULL DEFAULT 0.5              | Success rate defending this punch type   |
| `exposure_count`     | INTEGER | NOT NULL DEFAULT 0                | Times this punch has been thrown at user  |
| `last_updated`       | TEXT    | NOT NULL DEFAULT datetime('now')  | Last update timestamp                    |

### Table: `user_xp`

Singleton table (id always = 1) storing the user's XP and rank.

| Column             | Type    | Constraints / Default         | Description                        |
|--------------------|---------|-------------------------------|------------------------------------|
| `id`               | INTEGER | PRIMARY KEY CHECK(id = 1)     | Always 1 (singleton)               |
| `total_xp`         | INTEGER | NOT NULL DEFAULT 0            | Cumulative XP earned               |
| `current_rank`     | TEXT    | NOT NULL DEFAULT 'Novice'     | Current rank tier name             |
| `rank_history_json`| TEXT    | NOT NULL DEFAULT '[]'         | History of rank-up events as JSON  |

**Initialized on schema creation:** `INSERT OR IGNORE INTO user_xp (id, total_xp, current_rank, rank_history_json) VALUES (1, 0, 'Novice', '[]');`

### Table: `achievements`

Records unlocked achievements.

| Column          | Type    | Constraints / Default             | Description                  |
|-----------------|---------|-----------------------------------|------------------------------|
| `id`            | INTEGER | PRIMARY KEY AUTOINCREMENT         | Row ID                       |
| `achievement_id`| TEXT    | UNIQUE NOT NULL                   | Achievement identifier       |
| `unlocked_at`   | TEXT    | NOT NULL DEFAULT datetime('now')  | When the achievement unlocked|

### Table: `streaks`

Singleton table (id always = 1) tracking daily training streaks and weekly goals.

| Column             | Type    | Constraints / Default         | Description                          |
|--------------------|---------|-------------------------------|--------------------------------------|
| `id`               | INTEGER | PRIMARY KEY CHECK(id = 1)     | Always 1 (singleton)                 |
| `current_streak`   | INTEGER | NOT NULL DEFAULT 0            | Current consecutive training days    |
| `longest_streak`   | INTEGER | NOT NULL DEFAULT 0            | All-time longest streak              |
| `last_training_date`| TEXT   |                               | Date of most recent training session |
| `weekly_goal`      | INTEGER | NOT NULL DEFAULT 3            | Target training sessions per week    |
| `weekly_progress`  | INTEGER | NOT NULL DEFAULT 0            | Sessions completed this week         |
| `week_start_date`  | TEXT    |                               | Start date of current tracking week  |

**Initialized on schema creation:** `INSERT OR IGNORE INTO streaks (id, current_streak, longest_streak, weekly_goal, weekly_progress) VALUES (1, 0, 0, 3, 0);`

### Table: `personal_records`

Stores all-time personal bests.

| Column          | Type    | Constraints / Default             | Description                         |
|-----------------|---------|-----------------------------------|-------------------------------------|
| `id`            | INTEGER | PRIMARY KEY AUTOINCREMENT         | Row ID                              |
| `record_type`   | TEXT    | UNIQUE NOT NULL                   | Record category (e.g., 'max_force', 'best_reaction_ms') |
| `value`         | REAL    | NOT NULL DEFAULT 0.0              | Record value                        |
| `achieved_at`   | TEXT    | NOT NULL DEFAULT datetime('now')  | When the record was set             |
| `previous_value` | REAL   | NOT NULL DEFAULT 0.0              | Previous record value               |

---

## 4. Session Summary Fields

After each training session completes, `session_manager._build_summary()` generates a comprehensive summary stored in `training_sessions.summary_json`. The summary contains the following fields:

### Core Metrics

| Field                  | Type   | Description                                                |
|------------------------|--------|------------------------------------------------------------|
| `total_punches`        | int    | Total punches thrown by the user                           |
| `punch_distribution`   | dict   | Count per punch type (e.g., `{"jab": 12, "cross": 8}`)    |
| `force_distribution`   | dict   | Average force per punch type                               |
| `pad_distribution`     | dict   | Count per pad (centre, left, right, head)                  |
| `rounds_completed`     | int    | Number of rounds finished                                  |
| `duration_sec`         | float  | Total session duration in seconds                          |
| `punches_per_minute`   | float  | Average punch rate over the session                        |
| `max_power`            | float  | Highest single-punch force recorded                        |

### Robot/Defense Metrics (Sparring)

| Field                        | Type   | Description                                            |
|------------------------------|--------|--------------------------------------------------------|
| `robot_punches_thrown`       | int    | Total attacks by the robot                             |
| `robot_punches_landed`       | int    | Robot attacks that hit the user                        |
| `defense_rate`               | float  | (thrown - landed) / thrown                              |
| `defense_breakdown`          | dict   | Counts per defense type (block, slip, dodge, hit, unknown) |

### Movement Metrics

| Field                        | Type   | Description                                            |
|------------------------------|--------|--------------------------------------------------------|
| `avg_depth`                  | float  | Average depth (distance from camera)                   |
| `depth_range`                | list   | [min_depth, max_depth] during session                  |
| `lateral_movement`           | float  | Total lateral movement magnitude                       |
| `max_lateral_displacement`   | float  | Maximum single lateral displacement                    |
| `max_depth_displacement`     | float  | Maximum single depth displacement                      |

### Sensor Pipeline Metrics

| Field                        | Type   | Description                                            |
|------------------------------|--------|--------------------------------------------------------|
| `cv_prediction_summary`      | dict   | CV model prediction counts and confidence stats        |
| `imu_strike_summary`         | dict   | IMU impact counts per pad                              |
| `imu_strikes_total`          | int    | Total IMU-detected impacts                             |
| `direction_summary`          | dict   | Directional movement analysis                          |
| `imu_confirmation_rate`      | float  | Fraction of CV punches confirmed by IMU                |

### Experimental Metrics

| Field                        | Type   | Description                                            |
|------------------------------|--------|--------------------------------------------------------|
| `experimental.defense_reactions`   | list   | Per-attack defense reaction details              |
| `experimental.defense_rate`        | float  | Defense rate (experimental calculation)           |
| `experimental.defense_breakdown`   | dict   | Defense type counts (experimental)                |
| `experimental.avg_reaction_time_ms`| float  | Average reaction time to robot attacks (ms)       |

---

## 5. Gamification System

### Rank Tiers

BoxBunny uses a 6-tier ranking system based on cumulative XP:

| Rank       | XP Threshold | Description                     |
|------------|-------------:|---------------------------------|
| Novice     |            0 | Starting rank for all users     |
| Contender  |          500 | Beginning to train regularly    |
| Fighter    |        1,500 | Developing solid fundamentals   |
| Warrior    |        4,000 | Consistent and skilled          |
| Champion   |       10,000 | High-level proficiency          |
| Elite      |       25,000 | Top-tier dedication and skill   |

### XP Calculation

XP is awarded at the end of each completed session using the following formula:

```
total_xp = base_xp + completion_bonus + score_multiplier + streak_bonus
```

**Base XP by Mode:**

| Mode         | Base XP |
|--------------|--------:|
| Training     |      50 |
| Sparring     |      80 |
| Free         |      30 |
| Power Test   |      40 |
| Stamina Test |      40 |
| Reaction Test|      40 |

**Bonuses:**
- **Completion Bonus:** Additional XP for finishing all configured rounds.
- **Score Multiplier:** Scales with session performance (accuracy, defense rate, etc.).
- **Streak Bonus:** Additional XP when the user is on an active daily training streak.

### Achievements

BoxBunny defines **12+ achievements** that unlock based on specific accomplishments:

| Achievement ID   | Description                                                    |
|------------------|----------------------------------------------------------------|
| `first_blood`    | Complete your first training session                           |
| `century`        | Throw 100 punches in a single session                          |
| `fury`           | Achieve a high punch rate                                      |
| `iron_chin`      | Achieve a high defense rate in sparring                        |
| `weekly_warrior` | Meet your weekly training goal                                 |
| `well_rounded`   | Complete sessions in all training modes                        |
| `speed_demon`    | Achieve a Lightning tier in reaction test                      |
| `combo_breaker`  | Master a combo drill                                           |
| `power_surge`    | Set a new personal record for punch force                      |
| `marathon`       | Complete a long training session                               |
| `untouchable`    | Complete a sparring round without being hit                    |
| `perfect_round`  | Achieve 100% accuracy in a combo drill                         |
| `streak_master`  | Maintain a long daily training streak                          |
| `shadow_king`    | Complete a free training session with high engagement           |
| `ring_general`   | Demonstrate mastery across multiple sparring styles            |

Each achievement is recorded once in the `achievements` table with its unlock timestamp.

### Streaks

The streak system tracks training consistency:

- **Current Streak:** Number of consecutive days with at least one training session.
- **Longest Streak:** All-time record for consecutive training days.
- **Last Training Date:** Used to determine if the streak continues or resets.
- **Weekly Goal:** Configurable target (default: 3 sessions per week).
- **Weekly Progress:** Sessions completed in the current tracking week.
- **Week Start Date:** When the current weekly tracking period began.

Streaks reset to 0 if a full calendar day passes without training.

---

## 6. Population Benchmarks

**File:** `data/benchmarks/population_norms.json`

BoxBunny compares user performance against population norms derived from sports science literature. This enables percentile-based performance ratings.

### Metrics Covered

| Metric                     | Unit       | Direction    | Description                                      |
|----------------------------|------------|--------------|--------------------------------------------------|
| `reaction_time_ms`         | ms         | Lower better | Simple visual reaction time                      |
| `punches_per_minute`       | count/min  | Higher better| Sustained punch rate during 2-minute test        |
| `punch_force_normalized`   | 0-1 scale  | Higher better| Normalized punch force (scaled to pad IMU range) |
| `fatigue_index`            | 0-1 ratio  | Higher better| Late-round / early-round punch rate ratio        |
| `defense_rate`             | 0-1 ratio  | Higher better| Fraction of incoming punches defended             |
| `session_punch_count`      | count      | Higher better| Total punches in a standard 3x3min session       |

### Demographic Segmentation

Most metrics are segmented by:
- **Gender:** male, female
- **Age Group:** 18-24, 25-34, 35-44, 45-54, 55-64, 65+

The `defense_rate` and `session_punch_count` metrics are segmented by:
- **Gender:** male, female
- **Skill Level:** beginner, intermediate, advanced

### Percentile Breakpoints

Each demographic group provides five percentile values:

| Percentile | Label         |
|------------|---------------|
| p10        | Getting Started |
| p25        | Developing    |
| p50        | Average       |
| p75        | Above Average |
| p90        | Elite         |

**Example -- Reaction Time (male, 18-24):**

| Percentile | Value (ms) |
|------------|------------|
| p10        | 190        |
| p25        | 210        |
| p50        | 240        |
| p75        | 270        |
| p90        | 310        |

**Example -- Punches Per Minute (female, 25-34):**

| Percentile | Value |
|------------|-------|
| p10        | 26    |
| p25        | 38    |
| p50        | 52    |
| p75        | 67    |
| p90        | 82    |

### Tier Labels

Results are classified into human-readable tiers based on percentile range:

| Percentile Range | Tier Label       |
|------------------|------------------|
| >= p90           | Elite            |
| p75 to p90       | Advanced         |
| p50 to p75       | Above Average    |
| p25 to p50       | Average          |
| p10 to p25       | Developing       |
| < p10            | Getting Started  |

### Sources

The benchmark data is drawn from published sports science research:
- Welford (1980), Der & Deary (2006), Jain et al. (2015) -- Reaction time
- El-Ashker (2011), Davis et al. (2017) -- Punches per minute
- Pierce et al. (2006), Walilko et al. (2005) -- Punch force
- Ouergui et al. (2014) -- Fatigue index
- Thomson & Lamb (2016) -- Defense rate

---

## 7. Demo Users

**Seeder Tool:** `tools/demo_data_seeder.py`

Four demo accounts are pre-seeded for testing and demonstration purposes. All use simple passwords for easy access.

### Demo Account Credentials

| Username | Password     | User Type  |
|----------|-------------|------------|
| alex     | boxing123   | individual |
| maria    | boxing123   | individual |
| jake     | boxing123   | individual |
| sarah    | coaching123 | coach      |

### Alex -- Beginner

| Attribute      | Value                |
|----------------|----------------------|
| Level          | Beginner             |
| Age / Gender   | 22 / Male            |
| Sessions       | 8 training sessions  |
| Total XP       | 350                  |
| Rank           | Novice (0-499 XP)    |

Alex represents a new user who has just started training. Limited session history, low XP, and no advanced achievements.

### Maria -- Intermediate

| Attribute      | Value                    |
|----------------|--------------------------|
| Level          | Intermediate             |
| Age / Gender   | 28 / Female              |
| Sessions       | 35 training sessions     |
| Total XP       | 2,800                    |
| Rank           | Fighter (1,500-3,999 XP) |

Maria represents an active user with moderate experience. Has tried multiple training modes, has some combo masteries, and shows consistent progress.

### Jake -- Advanced

| Attribute      | Value                       |
|----------------|-----------------------------|
| Level          | Advanced                    |
| Age / Gender   | 31 / Male                   |
| Sessions       | 120 training sessions       |
| Total XP       | 12,000                      |
| Rank           | Champion (10,000-24,999 XP) |

Jake represents a dedicated, long-term user. Extensive session history across all modes, many achievements unlocked, strong performance metrics, and high combo mastery rates.

### Sarah -- Coach

| Attribute          | Value                   |
|--------------------|-------------------------|
| Level              | N/A (coach account)     |
| Age / Gender       | 35 / Female             |
| Coaching Sessions  | 3 group sessions run    |
| Presets            | 4 saved presets         |

Sarah represents a coach who manages group training. Her data demonstrates the coaching workflow with multiple participants per session and saved station presets.
