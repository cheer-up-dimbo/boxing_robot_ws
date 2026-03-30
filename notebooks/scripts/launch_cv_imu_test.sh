#!/bin/bash
# launch_cv_imu_test.sh -- Launches CV + IMU fusion test
#
# Spawns a separate terminal for micro-ROS agent + IMU bridge + Arm GUI V3
# (no conda), then runs the CV fusion test in the current shell (conda).
#
# Usage:  bash notebooks/scripts/launch_cv_imu_test.sh [TEENSY_PORT] [BAUD]
set +e

WS="/home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws"
cd "$WS"

TEENSY_PORT="${1:-/dev/ttyACM0}"
TEENSY_BAUD="${2:-115200}"
export DISPLAY="${DISPLAY:-:0}"

# ── Cleanup on exit ──
cleanup() {
    echo ""
    echo "=== Stopping CV + IMU Fusion Test ==="
    pkill -f "imu_udp_bridge" 2>/dev/null
    pkill -f "micro_ros_agent.*serial" 2>/dev/null
    pkill -f "unified_GUI_V3" 2>/dev/null
    sleep 1
    pkill -9 -f "imu_udp_bridge" 2>/dev/null
    pkill -9 -f "micro_ros_agent.*serial" 2>/dev/null
    pkill -9 -f "unified_GUI_V3" 2>/dev/null
    echo "All processes stopped."
}
trap cleanup EXIT INT TERM

# ── Write the IMU terminal script to a fixed path (not tmpfile) ──
IMU_SCRIPT="$WS/notebooks/scripts/_imu_terminal.sh"
cat > "$IMU_SCRIPT" << 'EOF'
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
EOF
chmod +x "$IMU_SCRIPT"

# ── Launch the IMU terminal ──
echo "=== Starting micro-ROS + IMU bridge + Arm GUI (separate terminal) ==="

if command -v gnome-terminal &>/dev/null; then
    gnome-terminal --title="BoxBunny IMU + Arm Control" -- \
        bash "$IMU_SCRIPT" "$TEENSY_PORT" "$TEENSY_BAUD" &
elif command -v xterm &>/dev/null; then
    xterm -title "BoxBunny IMU + Arm Control" -hold -e \
        bash "$IMU_SCRIPT" "$TEENSY_PORT" "$TEENSY_BAUD" &
else
    echo "No terminal emulator found. Running in background..."
    bash "$IMU_SCRIPT" "$TEENSY_PORT" "$TEENSY_BAUD" &
fi
sleep 5

# ── Main: CV inference with IMU fusion (conda) ──
echo ""
echo "=== Starting CV + IMU Fusion Test ==="
echo "Press 'q' in the display window to quit."
echo ""

eval "$(conda shell.bash hook 2>/dev/null)"
conda activate boxing_ai 2>/dev/null || true

python3 notebooks/scripts/cv_imu_fusion_test.py \
    --checkpoint action_prediction/model/best_model.pth \
    --pose-weights action_prediction/model/yolo26n-pose.pt \
    --show-video \
    2>&1

echo ""
echo "=== Test Complete ==="
