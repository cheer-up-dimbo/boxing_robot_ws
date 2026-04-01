#!/usr/bin/env bash
# Launch just the IMU pad simulator GUI.
set +e
cd /home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws
source /opt/ros/humble/setup.bash && source install/setup.bash

export QT_QPA_PLATFORM_PLUGIN_PATH=$(python3 -c "import PySide6; print(PySide6.__path__[0])")/Qt/plugins/platforms

echo "Launching IMU Simulator..."
echo "Pad mapping: LEFT=prev, RIGHT=next, CENTRE=enter, HEAD=back"
echo "Close the window to stop."
echo ""

python3 tools/imu_simulator.py 2>&1
