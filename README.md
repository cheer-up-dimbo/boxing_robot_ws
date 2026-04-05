# BoxBunny — AI-Powered Boxing Training Robot

> A real-time boxing training system combining computer vision, IMU sensor fusion, a 2-DOF robot punching arm, and a local AI coach — all running on-device with no internet required.

**Final-year engineering project** | Jetson Orin NX | ROS 2 Humble | 96.6% punch detection accuracy | 8-class classification at ~42 fps

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Hardware](#hardware)
- [Software Stack](#software-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Testing](#testing)
- [Demo Users](#demo-users)
- [Documentation](#documentation)
- [Notebook](#notebook)
- [Developer Guidelines](#developer-guidelines)
- [Assets & Licensing](#assets--licensing)
- [License](#license)

---

## Overview

BoxBunny is a production-grade boxing training system built on the NVIDIA Jetson Orin NX. A user stands in front of the robot, throws punches at IMU-equipped pads, and the system:

1. **Detects** what punch was thrown using a fused CV + IMU pipeline (FusionVoxelPoseTransformerModel, 96.6% accuracy, 8 classes)
2. **Responds** with a 2-DOF robot arm that throws back using Markov chain attack patterns across 5 AI fighting styles
3. **Coaches** in real-time via a local LLM (Qwen2.5-3B-Instruct) that provides technique tips, post-session analysis, and conversational Q&A
4. **Tracks** performance across sessions with gamification (XP, ranks, achievements, streaks) and population benchmarking

Everything runs locally on-device. The touchscreen GUI is designed for gloved hands (60px touch targets, pattern lock auth, IMU pad navigation), and a companion phone dashboard provides detailed analytics, AI chat, and coach station management over the local network.

---

## Features

### Training Modes

| Mode | Description |
|------|-------------|
| **Techniques** | 50 progressive combo drills (Beginner to Advanced) with real-time accuracy tracking and mastery scoring |
| **Sparring** | 5 AI styles (Boxer, Brawler, Counter-Puncher, Pressure, Switch) with Markov chain attacks, reactive counter-punches, and defense tracking |
| **Free Training** | Open reactive session — robot only counter-punches when you hit a pad, user controls the pace |
| **Performance Tests** | Power (IMU force measurement), Stamina (timed endurance), Reaction Time (visual stimulus + pose estimation) |
| **Coach Station** | Group circuit training with participant rotation, managed from the phone dashboard |

### Punch Detection and Sensor Fusion

- **CV Model**: FusionVoxelPoseTransformerModel — 8-class punch detection (jab, cross, left hook, right hook, left uppercut, right uppercut, block, idle) from depth voxels + pose features
- **TensorRT FP16 inference** at ~42 fps on Jetson Orin NX
- **IMU Sensors**: 4 pad IMUs (force classification: light/medium/hard) + 2 arm IMUs (defense tracking) via Teensy 4.1 microcontroller
- **Fusion Engine**: CV predictions buffered over 0.8s window; when an IMU pad strike fires, the system searches the buffer for the most frequent valid prediction using pad-constraint filtering (e.g., centre pad = jab/cross only, left pad = left hook/left uppercut only)
- **Defense Detection**: Block via CV model, slip/dodge via depth-based tracking
- **Person Tracking**: YOLO bounding box centre drives left/right/centre direction with 20px hysteresis for robot yaw motor tracking

### AI Coach (Local LLM)

- Qwen2.5-3B-Instruct running locally in GGUF format (Q4_K_M, ~2 GB) — no cloud APIs
- Real-time coaching tips during sessions (every 18s, context-aware)
- Post-session AI analysis with personalized drill suggestions
- Chat interface on phone dashboard for boxing Q&A
- 54 fallback tips (technique, encouragement, correction, suggestion) when LLM is unavailable
- Adaptive GPU sharing: CV node drops to 6 Hz when idle, freeing GPU for LLM inference

### Touchscreen GUI

- PySide6 dark theme, 1024x600, designed for gloved-hand interaction
- 24 pages, 11 reusable widgets
- IMU pad navigation (left = prev, right = next, centre = enter, head = back)
- Pattern lock authentication (SHA-256 hashed) — no typing with gloves
- Developer mode overlay showing live pad/arm activity and CV predictions
- 18 sound effects for session events

### Phone Dashboard

- Vue 3 + Tailwind CSS SPA served over local network (or public tunnel via localhost.run)
- QR code connection from the Jupyter notebook
- Login with password or Android-style pattern lock
- 6-question onboarding proficiency survey
- Dashboard with XP progress, weekly goals, training heatmap, peer comparison percentiles
- Training history with session cards, grades, and trend charts
- AI chat interface with the boxing coach
- Coach mode for station management and group training
- Preset save/load, CSV data export with date range filtering
- WebSocket for real-time session updates during training

### Gamification

| Rank Tier | XP Required |
|-----------|-------------|
| Novice | 0 |
| Contender | — |
| Fighter | — |
| Warrior | — |
| Champion | — |
| Elite | — |

- 12 achievements with SVG badges (first_blood, century, fury, thousand_fists, speed_demon, weekly_warrior, consistent, iron_chin, marathon, centurion, well_rounded, perfect_round)
- XP earned per session based on performance
- Streak tracking for consecutive training days
- Population benchmarks by age, gender, and skill level

---

## System Architecture

### Data Flow

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                        JETSON ORIN NX (On-Device)                      │
 │                                                                        │
 │  ┌──────────┐     ┌──────────┐                                         │
 │  │ RealSense│     │ Teensy   │                                         │
 │  │  D435i   │     │   4.1    │                                         │
 │  │ (RGB-D)  │     │ (6 IMUs) │                                         │
 │  └────┬─────┘     └────┬─────┘                                         │
 │       │ pyrealsense2   │ serial                                        │
 │       v                v                                               │
 │  ┌─────────┐     ┌──────────┐                                          │
 │  │ cv_node │     │ imu_node │                                          │
 │  │ (TRT    │     │ (pad +   │                                          │
 │  │  FP16)  │     │  arm IMU)│                                          │
 │  └─┬──┬──┬─┘     └──┬───┬──┘                                          │
 │    │  │  │           │   │                                             │
 │    │  │  │  PunchDet │   │ NavCommand                                  │
 │    │  │  │  + IMU    │   │                                             │
 │    │  │  │   Strike  │   v                                             │
 │    │  │  │    v      │  ┌────────────┐    ┌──────────────────────┐     │
 │    │  │  │  ┌────────┴──┤  punch_    │    │  PySide6 GUI         │     │
 │    │  │  │  │           │  processor ├───>│  (24 pages, 1024x600)│     │
 │    │  │  │  │  Fusion   │ (CV+IMU    │    │  touchscreen         │     │
 │    │  │  │  │           │  fusion)   │    └──────────────────────┘     │
 │    │  │  │  └─────┬─────┘                                              │
 │    │  │  │        │ ConfirmedPunch                                      │
 │    │  │  │        v                                                     │
 │    │  │  │  ┌──────────────┐    ┌───────────────┐                      │
 │    │  │  └─>│   session_   │<──>│  drill_       │                      │
 │    │  │     │   manager    │<──>│  manager      │                      │
 │    │  │     │ (lifecycle,  │    │ (50 combos)   │                      │
 │    │  │     │  data store) │    └───────────────┘                      │
 │    │  │     │              │    ┌───────────────┐    ┌──────────────┐  │
 │    │  │     │              │<──>│  sparring_    │───>│  robot_node  │  │
 │    │  │     │              │    │  engine       │    │ (arm + yaw + │  │
 │    │  │     └──────┬───────┘    │ (5 AI styles) │    │  height)     │  │
 │    │  │            │            └───────────────┘    └──────┬───────┘  │
 │    │  │            v                                        │          │
 │    │  │     ┌──────────────┐    ┌───────────────┐           │          │
 │    │  └────>│  analytics_  │    │   llm_node    │           v          │
 │    │        │  node        │    │ (Qwen2.5-3B)  │    ┌──────────────┐ │
 │    │        │ (stats,      │    │ coaching tips  │    │  2-DOF Arm   │ │
 │    │        │  trends)     │    └───────────────┘    │  (Dynamixel) │ │
 │    │        └──────────────┘                         └──────────────┘ │
 │    │  PersonDirection                                                  │
 │    v                                                                   │
 │  ┌────────────────────────────┐                                        │
 │  │ SQLite (main + per-user)   │<── FastAPI ──> Vue 3 Phone Dashboard  │
 │  └────────────────────────────┘     :8080       (WebSocket real-time)  │
 │                                                                        │
 └─────────────────────────────────────────────────────────────────────────┘
```

### ROS 2 Nodes

| Node | Role |
|------|------|
| `cv_node` | Direct camera access via pyrealsense2, TensorRT FP16 inference, punch detection + person tracking. Adaptive rate: 6 Hz idle / 30 Hz active |
| `imu_node` | Processes Teensy IMU data in dual mode (navigation vs training) |
| `robot_node` | Bridge to arm commands, height motor, yaw motor |
| `punch_processor` | CV + IMU fusion with pad-constraint filtering, defense event pipeline |
| `session_manager` | Session lifecycle, round management, comprehensive data collection |
| `drill_manager` | Combo drill validation, mastery scoring, progression tracking |
| `sparring_engine` | Markov chain attacks + reactive counter-punches across 5 AI styles |
| `analytics_node` | Statistics computation, trend analysis, population benchmarks |
| `llm_node` | Local LLM coaching tips + post-session analysis |
| `gesture_node` | MediaPipe hand gesture navigation (optional) |

### Message and Service Interfaces

- **21 custom ROS messages**: PunchDetection, PunchEvent, ConfirmedPunch, DefenseEvent, SessionState, DrillProgress, CoachTip, RobotCommand, UserTracking, PersonDirection, and more
- **6 custom ROS services**: StartSession, EndSession, StartDrill, GenerateLlm, SetImuMode, CalibrateImuPunch

---

## Hardware

| Component | Details |
|-----------|---------|
| **Compute** | NVIDIA Jetson Orin NX (8 GB), Ubuntu 22.04, CUDA |
| **Camera** | Intel RealSense D435i (RGB 960x540, Depth 848x480 @ 30 fps). Opened directly via pyrealsense2 (not ROS driver) due to D435i HID bug on Jetson |
| **IMU Sensors** | 6x MPU6050 on Teensy 4.1 — 4 pads (centre, left, right, head) + 2 arms |
| **Robot Arm** | 2-DOF arm with Dynamixel servos, 6 punch types, IK-safe Bezier motion paths |
| **Height Motor** | Auto-adjusts to user height via YOLO person detection; manual control from GUI or phone |
| **Yaw Motor** | Tracks user left/right/centre position via CV person direction |
| **Display** | 7" touchscreen (1024x600), gloved-hand optimized |

---

## Software Stack

| Layer | Technology |
|-------|-----------|
| **Middleware** | ROS 2 Humble (10 nodes, 21 messages, 6 services) |
| **CV / ML** | PyTorch, TensorRT FP16, YOLO (ultralytics), ONNX Runtime |
| **Touchscreen GUI** | PySide6 (24 pages, 11 widgets, dark theme) |
| **Phone Dashboard** | FastAPI backend (7 API modules) + Vue 3 / Tailwind CSS frontend (10 views, 8 components) |
| **Database** | SQLite, 2-tier: main DB (users, sessions, auth) + per-user DBs (XP, streaks, records) |
| **AI Coach** | Qwen2.5-3B-Instruct (GGUF Q4_K_M, ~2 GB), llama-cpp-python with CUDA |
| **Sensors** | pyrealsense2 (D435i), pyserial (Teensy 4.1) |
| **Build** | colcon (ROS 2 build tool), Vite (Vue 3 frontend) |

---

## Project Structure

```
boxing_robot_ws/
├── action_prediction/          # Trained CV model (DO NOT MODIFY)
│   ├── lib/                    #   Inference engine (fusion_model, pose, voxel)
│   ├── model/                  #   Weights (.pth, .onnx, .trt, YOLO)
│   └── run.py                  #   Standalone inference script
│
├── src/
│   ├── boxbunny_msgs/          # 21 ROS messages + 6 services
│   ├── boxbunny_core/          # 10 ROS 2 nodes + 4 launch files
│   ├── boxbunny_gui/           # PySide6 touchscreen GUI (24 pages, 11 widgets)
│   │   └── assets/sounds/      #   18 sound effects
│   └── boxbunny_dashboard/     # FastAPI + Vue 3 phone dashboard
│       ├── boxbunny_dashboard/  #   Python backend (7 API modules)
│       ├── frontend/           #   Vue 3 source (10 views, 8 components)
│       └── static/dist/        #   Built SPA
│
├── Boxing_Arm_Control/         # Robot arm firmware + control (Teensy/Dynamixel)
│
├── config/                     # All configuration (no magic numbers in code)
│   ├── boxbunny.yaml           #   Master system config
│   ├── ros_topics.yaml         #   All ROS topic & service names
│   ├── drills.yaml             #   50 combo drill definitions
│   ├── sparring.yaml           #   5 sparring style transition matrices
│   ├── fallback_tips.json      #   54 AI coach fallback tips
│   ├── llm_system_prompt.txt   #   LLM persona configuration
│   └── llm_models.yaml         #   Available LLM models
│
├── data/
│   ├── boxbunny_main.db        # Main SQLite database
│   ├── users/                  # Per-user SQLite databases
│   ├── benchmarks/             # Population performance norms (age/gender)
│   ├── boxing_knowledge/       # 9 RAG documents for AI coach context
│   ├── punch_sequences/        # 8 robot punch waypoint files (JSON)
│   └── schema/                 # SQLite schema files (main + user)
│
├── models/
│   └── llm/                    # Qwen2.5-3B-Instruct Q4_K_M (~2 GB GGUF)
│
├── tools/
│   ├── teensy_simulator.py     # Teensy hardware simulator GUI
│   ├── llm_chat_gui.py         # Standalone LLM chat interface
│   └── demo_data_seeder.py     # Create demo users with training history
│
├── notebooks/
│   ├── boxbunny_runner.ipynb   # Master notebook (12 sections + 3 appendix)
│   └── scripts/                # Extracted notebook helper scripts
│
├── tests/                      # 146 pytest tests
├── scripts/                    # setup.sh, download_models.sh
├── docs/                       # Full technical documentation
└── _archive/                   # Archived old code (not used at runtime)
```

---

## Quick Start

### Prerequisites

- NVIDIA Jetson Orin NX (8 GB) with JetPack 5.x
- ROS 2 Humble installed
- Python 3.10
- CUDA toolkit (for TensorRT and LLM inference)

### 1. Bootstrap (first time)

```bash
cd boxing_robot_ws
bash scripts/setup.sh
```

### 2. Build and seed demo data

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
python3 tools/demo_data_seeder.py
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-jetson.txt   # Jetson-specific wheels
bash scripts/download_models.sh          # Download LLM model (~2 GB)
```

### 4. Run in development mode (with Teensy simulator)

```bash
ros2 launch boxbunny_core boxbunny_dev.launch.py
```

### 5. Run in production (real hardware)

```bash
ros2 launch boxbunny_core boxbunny_full.launch.py
```

### 6. Phone dashboard

```bash
# Option A: From the Jupyter notebook (includes public tunnel + QR code)
jupyter notebook notebooks/boxbunny_runner.ipynb
# Run the "Phone Dashboard" cell

# Option B: Manual
python3 -m boxbunny_dashboard.server
# Open http://<jetson-ip>:8080 on your phone
```

### Launch Files

| Launch File | Description |
|-------------|-------------|
| `boxbunny_dev.launch.py` | All nodes + Teensy simulator + GUI (development) |
| `boxbunny_full.launch.py` | All nodes with real hardware (production) |
| `headless.launch.py` | Processing nodes only, no GUI |
| `teensy_simulator.launch.py` | Teensy simulator standalone |

---

## Configuration

All system configuration lives in `config/`. No magic numbers in code.

| File | Purpose |
|------|---------|
| `boxbunny.yaml` | Master config: thresholds, timeouts, model paths, network settings |
| `ros_topics.yaml` | Every ROS topic and service name (loaded by `constants.py`) |
| `drills.yaml` | 50 combo definitions with timing, sequence, and difficulty parameters |
| `sparring.yaml` | 5 style transition matrices + difficulty scaling curves |
| `fallback_tips.json` | 54 coaching tips (4 categories) used when LLM is unavailable |
| `llm_system_prompt.txt` | LLM persona and behavior instructions |
| `llm_models.yaml` | Available LLM model paths and configurations |

To rename a ROS topic, edit `config/ros_topics.yaml` and restart. All nodes load topic names from there via `constants.py`.

---

## Testing

```bash
source /opt/ros/humble/setup.bash && source install/setup.bash
python3 -m pytest tests/ -v
```

146 tests covering:

- ROS node initialization and communication
- CV + IMU fusion logic and pad-constraint filtering
- Session lifecycle and data collection
- Drill validation and mastery scoring
- Sparring engine Markov chain transitions
- Database operations (main and per-user)
- Dashboard API endpoints and authentication
- Gamification (XP, ranks, achievements, streaks)

Tests can also be run from the master notebook (cell 2).

---

## Demo Users

Pre-seeded demo accounts for testing all skill levels:

| User | Password | Level | Profile | Sessions | Rank |
|------|----------|-------|---------|----------|------|
| alex | boxing123 | Beginner | M, 22, 175 cm, 72 kg | 8 | Novice |
| maria | boxing123 | Intermediate | F, 28, 165 cm, 58 kg | 35 | Fighter |
| jake | boxing123 | Advanced | M, 31, 183 cm, 85 kg | 120 | Champion |
| sarah | coaching123 | Coach | F, 35 | 3 coaching | -- |

Seed these accounts with: `python3 tools/demo_data_seeder.py`

---

## Documentation

Detailed technical documentation is in the `docs/` folder:

| Document | Contents |
|----------|----------|
| [architecture.md](docs/architecture.md) | System overview, node architecture, ROS topic graph, data flows, design philosophy |
| [cv_pipeline.md](docs/cv_pipeline.md) | CV model, inference pipeline, CV+IMU fusion algorithm, person tracking |
| [teensy_simulator.md](docs/teensy_simulator.md) | Simulator GUI, execute/auto mode, hardware forwarding, combo system |
| [data_collection.md](docs/data_collection.md) | Data sources, collection strategy, session summary, database schema |
| [dashboard_and_llm.md](docs/dashboard_and_llm.md) | Phone dashboard, API endpoints, AI coach, LLM reliability, height control |
| [sparring_and_training.md](docs/sparring_and_training.md) | Training modes, sparring engine, free mode, robot arm control |
| [gui_and_user_experience.md](docs/gui_and_user_experience.md) | GUI pages, UX design (gloved hands, pattern lock, IMU nav), calibration workflow |
| [testing_and_notebook.md](docs/testing_and_notebook.md) | Notebook sections, pytest suite, integration tests, manual testing guide |

Additional documentation organized by subsystem:

| Folder | Contents |
|--------|----------|
| `docs/gui/` | GUI architecture, page inventory, design system |
| `docs/dashboard/` | Backend API reference, frontend views, WebSocket protocol |
| `docs/system/` | ROS architecture, integration details, communication patterns |
| `docs/training/` | Training mode logic, sparring AI, combo drill design |
| `docs/data/` | Database schema, data collection pipeline |

### Dashboard API Reference

| Module | Prefix | Key Endpoints |
|--------|--------|---------------|
| `auth` | `/api/auth` | Login, signup, pattern login, profile update, set pattern, logout |
| `sessions` | `/api/sessions` | Current session, history, detail, trends, raw data |
| `gamification` | `/api/gamification` | XP/rank profile, achievements, leaderboard, benchmarks |
| `chat` | `/api/chat` | Send message, chat history |
| `coach` | `/api/coach` | Load config, start/end station, live participants |
| `presets` | `/api/presets` | CRUD for training presets, favorites |
| `remote` | `/api/remote` | GUI commands, presets, height control |
| `export` | `/api/export` | CSV export by session or date range |
| WebSocket | `/ws` | Real-time session state updates |

---

## Notebook

The master notebook (`notebooks/boxbunny_runner.ipynb`) provides all essential operations:

| # | Section | Description |
|---|---------|-------------|
| 1 | Build & Setup | `colcon build` + seed demo data |
| 2 | Run Tests | Full pytest suite (146 tests) |
| 3 | System Check | Hardware, dependencies, and model status |
| 4 | Launch System | Start all ROS nodes + Teensy simulator + GUI |
| 5 | Stop System | Kill all BoxBunny processes |
| 6 | GUI Test | Launch touchscreen GUI for visual inspection |
| 7 | Phone Dashboard | Server + public tunnel + QR code for phone access |
| 8 | CV Model Live Test | Camera feed with pose skeleton + action labels |
| 9 | LLM Coach Test | Interactive AI coach chat GUI |
| 10 | Build Vue Frontend | Rebuild phone dashboard SPA after changes |
| 11 | Sound Test | Play all 18 sound effects |
| 12 | Demo Profiles & Benchmarks | User profile cards + percentile rankings |

---

## Developer Guidelines

See `CLAUDE.md` for the full development rules. Key points:

- **Never delete files** -- archive to `_archive/`
- **Never modify** `action_prediction/lib/` model files (fusion_model.py, pose.py, voxel_features.py, voxel_model.py)
- All configurable values in YAML configs under `config/` -- no magic numbers in code
- All ROS topic names in `config/ros_topics.yaml`, loaded by `constants.py`
- Use `logging` module, never `print()`
- Max ~300 lines per file, type hints on all function signatures
- Docstrings, specific exception handling, structured logging

---

## Assets & Licensing

### Sound Effects

18 sound effects in `src/boxbunny_gui/assets/sounds/` sourced from Envato Elements and Mixkit (free license).

### Visual Assets

| Asset Set | Location | Count |
|-----------|----------|-------|
| Dashboard Avatars | `src/boxbunny_dashboard/frontend/public/avatars/` | 8 SVG icons |
| Achievement Badges | `src/boxbunny_dashboard/frontend/public/achievements/` | 12 SVG icons |
| Rank Badges | `src/boxbunny_dashboard/frontend/public/ranks/` | 6 SVG icons |

---

## License

Proprietary. All rights reserved.
