# BoxBunny Documentation

Complete technical documentation for the BoxBunny AI boxing training system.

---

## Documentation Map

### GUI (Desktop Application)

| Document | Description |
|----------|-------------|
| [gui/architecture.md](gui/architecture.md) | Application structure, page system, ROS bridge, navigation, sound, session tracking |
| [gui/design-system.md](gui/design-system.md) | Color palette, typography, spacing, button/card styles, accessibility |

### Dashboard (Phone Web App)

| Document | Description |
|----------|-------------|
| [dashboard/backend.md](dashboard/backend.md) | FastAPI server, authentication, API endpoints, database manager, WebSocket |
| [dashboard/frontend.md](dashboard/frontend.md) | Vue 3 SPA, router, Pinia stores, views, components, real-time updates |

### System Architecture

| Document | Description |
|----------|-------------|
| [system/architecture.md](system/architecture.md) | ROS 2 nodes, message types, topics, services, launch configurations |
| [system/integration.md](system/integration.md) | GUI-Dashboard-Core communication, remote commands, auth flow, data flow examples |
| [system/technical-deep-dive.md](system/technical-deep-dive.md) | Hardware specs, CV FPS sensitivity, LLM pipeline, GPU sharing, integration challenges, testing strategy |

### Training

| Document | Description |
|----------|-------------|
| [training/modes.md](training/modes.md) | Combo drills, sparring AI (5 styles), free training, performance tests, coach station |

### Data

| Document | Description |
|----------|-------------|
| [data/schema.md](data/schema.md) | Database schema (main + per-user), session summary fields, gamification, benchmarks |

### Operations

| Document | Description |
|----------|-------------|
| [testing.md](testing.md) | 146 pytest tests, integration tests, notebook-based testing |
| [deployment.md](deployment.md) | Hardware setup, build, launch configs, configuration, troubleshooting |

---

## Quick Reference

### External Dependencies

| Package | GUI | Dashboard | Core |
|---------|-----|-----------|------|
| ROS 2 Humble | via bridge | - | primary |
| PySide6 (Qt 6) | primary | - | - |
| FastAPI + Uvicorn | - | primary | - |
| Vue 3 + Tailwind | - | frontend | - |
| PyTorch + TensorRT | - | - | CV inference |
| pyrealsense2 | reaction test | - | camera |
| SQLite | db_helper | DatabaseManager | analytics |
| llama-cpp-python | - | chat API | LLM node |

### Key Files

| Purpose | File |
|---------|------|
| Master config | `config/boxbunny.yaml` |
| Topic registry | `config/ros_topics.yaml` |
| Main database | `data/boxbunny_main.db` |
| User databases | `data/users/{username}/boxbunny.db` |
| DB schemas | `data/schema/main_schema.sql`, `data/schema/user_schema.sql` |
| Demo data | `tools/demo_data_seeder.py` |
| Notebook runner | `notebooks/boxbunny_runner.ipynb` |

### Architecture Overview

```
                    Phone (Vue 3 SPA)
                         |
                    HTTP / WebSocket
                         |
                  FastAPI Dashboard -----> SQLite DBs <----- PySide6 GUI
                         |                                       |
                         |                              GuiBridge (QThread)
                         |                                       |
                    /tmp JSON files <----------------------- ROS 2 Nodes
                                                                 |
                                              +---------+---------+---------+
                                              |         |         |         |
                                          cv_node  imu_node  session_mgr  robot_node
                                              |         |                    |
                                         RealSense   Teensy            Robot Arm
                                          D435i       4.1              (Dynamixel)
```
