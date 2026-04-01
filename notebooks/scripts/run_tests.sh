#!/usr/bin/env bash
# Run all pytest tests.
set +e
cd /home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws
source /opt/ros/humble/setup.bash && source install/setup.bash
python3 -m pytest tests/ -v --tb=short 2>&1
