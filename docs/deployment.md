# BoxBunny Deployment Guide

## Hardware Requirements

| Component | Model | Purpose |
|-----------|-------|---------|
| Compute | Jetson Orin NX 8GB | Main processor (GPU for CV + LLM) |
| Camera | Intel RealSense D435i | RGB-D depth camera (30fps, 960x540) |
| IMU | Teensy 4.1 | 4 pad sensors + 2 arm sensors (accelerometer) |
| Robot Arm | 2-DOF (Dynamixel servos) | Punching arm with yaw + strike DOF |
| Display | 7" touchscreen (1024x600) | PySide6 GUI |
| Network | WiFi AP ("BoxBunny") | Phone dashboard access |

---

## Software Prerequisites

```bash
# ROS 2 Humble
sudo apt install ros-humble-desktop

# Python dependencies
pip install pyside6 fastapi uvicorn websockets bcrypt qrcode pyyaml

# Conda environment (for CV inference)
conda create -n boxing_ai python=3.10
conda activate boxing_ai
pip install torch torchvision pyrealsense2 ultralytics onnxruntime tensorrt

# Vue frontend (one-time build)
cd src/boxbunny_dashboard/frontend
npm install && npm run build
```

---

## Build

```bash
cd boxing_robot_ws

# Source ROS
source /opt/ros/humble/setup.bash

# Build all packages
colcon build --symlink-install

# Source workspace
source install/setup.bash
```

---

## Launch Configurations

### Development Mode (with Teensy Simulator)

```bash
ros2 launch boxbunny_core boxbunny_dev.launch.py
```

Launches: All ROS nodes + GUI + Teensy Simulator window. No real hardware needed.

### Production Mode (real hardware)

```bash
ros2 launch boxbunny_core boxbunny_full.launch.py
```

Launches: All ROS nodes + GUI. Requires RealSense camera, Teensy, and robot arm.

### Headless Mode (nodes only)

```bash
ros2 launch boxbunny_core headless.launch.py
```

Launches: ROS nodes without GUI. Useful for dashboard-only operation.

### Simulator Standalone

```bash
ros2 launch boxbunny_core teensy_simulator.launch.py
```

Launches: Only the Teensy Simulator for testing.

---

## Phone Dashboard

```bash
# Start dashboard server
python3 tools/dashboard_server.py

# Or directly
python3 -m boxbunny_dashboard.server
```

Access at `http://<jetson-ip>:8080` from any phone on the same network.

The dashboard serves the pre-built Vue SPA and provides REST API + WebSocket endpoints.

---

## Configuration

### Master Config: `config/boxbunny.yaml`

All tunable parameters in one file:

- **cv**: Model paths, confidence thresholds, inference settings
- **fusion**: CV+IMU fusion window, defense thresholds, pad mapping
- **imu**: Debounce timing, heartbeat interval
- **robot**: Serial port, baud rate, punch sequences
- **llm**: Model path, GPU layers, context window, temperature
- **training**: Default rounds, work/rest times, countdown
- **network**: WiFi SSID, dashboard port
- **database**: DB paths, guest session TTL

### Topic Registry: `config/ros_topics.yaml`

All ROS topic and service names. Loaded by `constants.py` at startup. Change topic names here without touching Python code.

---

## Database

Databases are auto-created on first run. To seed demo data:

```bash
python3 tools/demo_data_seeder.py          # Create demo users
python3 tools/demo_data_seeder.py --clean   # Wipe and recreate
```

Database locations:
- `data/boxbunny_main.db` — Shared user/auth database
- `data/users/<username>/boxbunny.db` — Per-user training data

---

## Directory Structure

```
boxing_robot_ws/
├── config/                 — YAML configuration files
├── data/                   — SQLite databases, schemas, benchmarks
│   ├── schema/             — SQL schema definitions
│   ├── benchmarks/         — Population performance norms
│   ├── boxing_knowledge/   — RAG documents for LLM
│   └── punch_sequences/    — Robot arm trajectory files
├── src/
│   ├── boxbunny_core/      — ROS 2 nodes (10 nodes)
│   │   └── launch/         — Launch files
│   ├── boxbunny_gui/       — PySide6 touchscreen GUI
│   │   └── assets/         — Fonts, sounds
│   ├── boxbunny_dashboard/ — FastAPI + Vue 3 dashboard
│   │   ├── api/            — REST API routers
│   │   ├── db/             — Database manager
│   │   └── frontend/       — Vue 3 SPA source
│   └── boxbunny_msgs/      — ROS message/service definitions
├── action_prediction/      — CV model (training + inference)
├── Boxing_Arm_Control/     — Robot arm firmware
├── tools/                  — Teensy simulator, demo seeder, utilities
├── tests/                  — pytest test suite
├── notebooks/              — Jupyter runner notebook
│   └── scripts/            — Helper bash/python scripts
├── models/                 — LLM model files (GGUF)
├── docs/                   — Project documentation
└── log/                    — Runtime logs
```

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| RealSense not detected | Check USB connection, run `rs-enumerate-devices` |
| CUDA out of memory | CV and LLM share GPU; reduce `n_gpu_layers` in config |
| Teensy not found | Check `/dev/ttyACM0`, verify micro-ROS agent running |
| GUI won't start | Ensure PySide6 installed, check `QT_QPA_PLATFORM_PLUGIN_PATH` |
| Dashboard 404 | Run `npm run build` in `src/boxbunny_dashboard/frontend/` |
| Pattern lock fails | Run `python3 tools/demo_data_seeder.py --clean` to reset |
| No sound | Check ALSA config, verify `assets/sounds/` directory exists |

---

## Jupyter Notebook

The primary operational interface is `notebooks/boxbunny_runner.ipynb`. Open in JupyterLab:

```bash
jupyter lab notebooks/boxbunny_runner.ipynb
```

The notebook contains 12 operational sections + 3 appendix sections covering build, test, launch, and debug workflows. See [docs/testing.md](testing.md) for details.
