#!/bin/bash
set +e

WS="/home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws"
TEENSY_PORT="${1:-/dev/ttyACM0}"
TEENSY_BAUD="${2:-115200}"

# Strip conda from PATH
export PATH=$(echo "$PATH" | tr ':' '\n' | grep -v conda | tr '\n' ':')
unset CONDA_DEFAULT_ENV CONDA_PREFIX CONDA_EXE CONDA_PYTHON_EXE
export DISPLAY="${DISPLAY:-:0}"

source /opt/ros/humble/setup.bash
[ -f "$HOME/microros_ws/install/local_setup.bash" ] && source "$HOME/microros_ws/install/local_setup.bash"
[ -f "$WS/install/setup.bash" ] && source "$WS/install/setup.bash"

echo "============================================"
echo "  BoxBunny IMU + Arm Control Terminal"
echo "============================================"
echo ""

echo "[1/3] Starting micro-ROS agent on $TEENSY_PORT @ $TEENSY_BAUD ..."
ros2 run micro_ros_agent micro_ros_agent serial --dev "$TEENSY_PORT" -b "$TEENSY_BAUD" &
AGENT_PID=$!
sleep 3

echo "[2/3] Starting IMU UDP bridge..."
python3 "$WS/notebooks/scripts/imu_udp_bridge.py" &
BRIDGE_PID=$!
sleep 1

echo "[3/3] Starting Boxing Arm Control GUI (V3)..."
python3 "$WS/Boxing_Arm_Control/ros2_ws/unified_GUI_V3.py" &
GUI_PID=$!

echo ""
echo "Running: agent=$AGENT_PID  bridge=$BRIDGE_PID  arm_gui=$GUI_PID"
echo "Close the V3 GUI window or press Ctrl+C to stop."
echo ""

wait $GUI_PID 2>/dev/null
echo ""
echo "V3 GUI exited. Cleaning up..."
kill $AGENT_PID $BRIDGE_PID 2>/dev/null
sleep 1
kill -9 $AGENT_PID $BRIDGE_PID 2>/dev/null
echo "Done. Press Enter to close this terminal."
read
