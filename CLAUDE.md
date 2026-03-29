# BoxBunny Boxing Training Robot

## Project Overview
Production boxing training robot on Jetson Orin NX 16GB with ROS 2 Humble.
Hardware: D435i depth camera, 6 IMU sensors (4 pads + 2 arms), robot arm (Teensy), height motor, 10.1" 1024x600 touchscreen.

## Architecture
- **ROS 2 Humble** workspace with 4 packages in `src/`
- **boxbunny_msgs**: Custom messages (21) and services (6)
- **boxbunny_core**: 9 processing nodes (cv, imu, robot, punch_processor, session_manager, drill_manager, sparring_engine, analytics, llm)
- **boxbunny_gui**: PySide6 touchscreen GUI (dark theme, 1024x600)
- **boxbunny_dashboard**: FastAPI mobile dashboard (Vue 3 SPA)
- **action_prediction/**: Trained CV model (DO NOT MODIFY model architecture)

## Key Files
- `src/boxbunny_core/boxbunny_core/constants.py` — Single source of truth for ALL topic names
- `config/boxbunny.yaml` — Master configuration
- `config/drills.yaml` — 50 combo drill definitions
- `config/sparring.yaml` — 5 sparring style matrices

## Build & Run
```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch boxbunny_core boxbunny_dev.launch.py  # Dev mode with IMU simulator
ros2 launch boxbunny_core boxbunny_full.launch.py  # Full production
```

## Critical Rules
1. **NEVER delete files** — archive to `_archive/`
2. **NEVER touch files outside** `boxing_robot_ws/`
3. **NEVER modify** `action_prediction/lib/fusion_model.py`, `pose.py`, `voxel_features.py`, `voxel_model.py`
4. All configurable values in YAML configs or `constants.py` — no magic numbers
5. No `print()` — use `logging` module
6. Max ~300 lines per file
7. Type hints on all function signatures
