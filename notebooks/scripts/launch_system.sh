#!/usr/bin/env bash
# Launch all ROS nodes + IMU simulator + GUI.
# Press Ctrl+C or notebook STOP to shut down.
set +e
cd /home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws
source /opt/ros/humble/setup.bash && source install/setup.bash

cleanup() {
    echo ""
    echo "=== Stopping BoxBunny ==="
    kill -- -$LAUNCH_PID 2>/dev/null
    sleep 1
    kill -9 -- -$LAUNCH_PID 2>/dev/null
    pkill -9 -f 'imu_simulator.py' 2>/dev/null
    pkill -9 -f 'gui_main' 2>/dev/null
    pkill -9 -f 'ros2.launch' 2>/dev/null
    fuser -k 8080/tcp 2>/dev/null
    echo "All processes and windows stopped."
}
trap cleanup EXIT INT TERM

echo "Launching BoxBunny in dev mode..."
setsid ros2 launch boxbunny_core boxbunny_dev.launch.py &
LAUNCH_PID=$!
sleep 5

echo ""
echo "=== Active ROS Nodes ==="
ros2 node list 2>/dev/null || echo "(nodes still starting...)"
echo ""
echo "=== RUNNING — Press STOP to shut down ==="

wait $LAUNCH_PID
