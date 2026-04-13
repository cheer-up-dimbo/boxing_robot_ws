#!/usr/bin/env bash
# =============================================================================
# 4d. Base Tracking Test — CV person direction → BLE base rotation
# =============================================================================
# Launches:
#   1. CV model with ROS (publishes /boxbunny/cv/person_direction)
#   2. BLE tracking script (connects to Arduino, sends L:/R:/S commands)
#
# Requires: RealSense D435i, conda boxing_ai, BoxBunny Base Arduino powered on.
# Press Ctrl+C / STOP to shut down.
# =============================================================================
set +e

WS="/home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws"
export DISPLAY="${DISPLAY:-:0}"

cleanup() {
    echo ""
    echo "=== Stopping Base Tracking Test ==="
    pkill -f 'test_base_tracking' 2>/dev/null
    pkill -f 'run_with_ros' 2>/dev/null
    pkill -f 'live_voxelflow' 2>/dev/null
    sleep 0.5
    fuser -k /dev/video* 2>/dev/null
    kill -- -$$ 2>/dev/null
    sleep 0.5
    kill -9 -- -$$ 2>/dev/null
    echo "All stopped."
}
trap cleanup EXIT INT TERM

# Kill stale processes
pkill -9 -f 'run_with_ros' 2>/dev/null
pkill -9 -f 'live_voxelflow' 2>/dev/null
pkill -9 -f 'test_base_tracking' 2>/dev/null
fuser -k /dev/video* 2>/dev/null
sleep 0.5

# ── Step 1: CV model with ROS (conda for PyTorch, ROS for publishing) ──
echo "=== Starting CV Model (with ROS person direction) ==="
eval "$(conda shell.bash hook 2>/dev/null)"
conda activate boxing_ai 2>/dev/null || true
source /opt/ros/humble/setup.bash
source "$WS/install/setup.bash" 2>/dev/null

cd "$WS/action_prediction"
CV_HEADLESS=1 python3 "$WS/notebooks/scripts/run_with_ros.py" &
CV_PID=$!
echo "  CV model starting (PID: $CV_PID)"
echo "  Waiting for camera + model to load..."
sleep 8

# Verify CV is running
if ! kill -0 $CV_PID 2>/dev/null; then
    echo "ERROR: CV model failed to start. Check camera connection."
    exit 1
fi
echo "  CV model running — person direction publishing"
echo ""

# ── Step 2: BLE tracking script ──────────────────────────────────────
echo "=== Starting BLE Base Tracking ==="
cd "$WS"
python3 "$WS/notebooks/scripts/test_base_tracking.py"
