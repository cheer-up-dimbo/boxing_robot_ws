#!/usr/bin/env bash
# Build the ROS 2 workspace and seed demo data.
set +e
cd /home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws
source /opt/ros/humble/setup.bash

echo "=== Building Workspace ==="
colcon build --symlink-install 2>&1
echo ""
source install/setup.bash
echo "=== Packages ==="
ros2 pkg list 2>/dev/null | grep boxbunny || echo "(build failed)"
echo ""
echo "=== Seeding Demo Data ==="
python3 tools/demo_data_seeder.py
