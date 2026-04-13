#!/usr/bin/env bash
# Run the CV action prediction model with live camera feed.
# Runs run.py from inside the action_prediction folder so all
# default paths resolve correctly. Uses conda boxing_ai for PyTorch.
set +e

WS="/home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws"
export DISPLAY="${DISPLAY:-:0}"

# Kill all children on exit (ensures camera is released)
cleanup() {
    kill -- -$$ 2>/dev/null
    pkill -9 -f 'run.py' 2>/dev/null
    pkill -9 -f 'live_voxelflow' 2>/dev/null
    sleep 0.5
    fuser -k /dev/video* 2>/dev/null
    kill -9 -- -$$ 2>/dev/null
}
trap cleanup EXIT INT TERM

# Kill stale processes
pkill -9 -f 'run_with_ros' 2>/dev/null
pkill -9 -f 'live_voxelflow' 2>/dev/null
pkill -9 -f 'run.py' 2>/dev/null
fuser -k /dev/video* 2>/dev/null
sleep 0.5

# Activate conda for torch/ultralytics/pyrealsense2
eval "$(conda shell.bash hook 2>/dev/null)"
conda activate boxing_ai 2>/dev/null || true

SHOW_VIDEO=""
MIN_CONF=""
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --show-video|--video)
            SHOW_VIDEO="--show-video"
            shift ;;
        --min-confidence)
            MIN_CONF="--min-confidence $2"
            shift 2 ;;
        --min-confidence=*)
            MIN_CONF="--min-confidence ${1#*=}"
            shift ;;
        *)
            EXTRA_ARGS+=("$1")
            shift ;;
    esac
done

if [[ -n "$SHOW_VIDEO" ]]; then
    echo "=== CV Model Live Test (with video feed) ==="
else
    echo "=== CV Model Live Test ==="
    echo "  (add --show-video for camera feed)"
fi
[[ -n "$MIN_CONF" ]] && echo "Confidence filter: $MIN_CONF"
echo "Stand 1.5-2m from camera."
echo "Close the window or press Ctrl+C to stop."
echo ""

# Run from inside action_prediction/ so default paths work
cd "$WS/action_prediction"
python3 run.py $SHOW_VIDEO $MIN_CONF "${EXTRA_ARGS[@]}" \
    2>&1 || echo "(D435i camera not connected or models missing)"
