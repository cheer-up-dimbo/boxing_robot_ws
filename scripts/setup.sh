#!/bin/bash
# BoxBunny Bootstrap Script
# One-command setup for fresh Jetson or dev machine
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$WS_ROOT"

echo "========================================="
echo "  BoxBunny Setup Script v1.0"
echo "========================================="
echo ""

# --- 1. Check prerequisites ---
echo "[1/7] Checking prerequisites..."

if ! command -v ros2 &>/dev/null; then
    echo "ERROR: ROS 2 not found. Install ROS 2 Humble first."
    echo "  See: https://docs.ros.org/en/humble/Installation.html"
    exit 1
fi
echo "  ROS 2: $(ros2 --version 2>/dev/null || echo 'found')"

if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 not found."
    exit 1
fi
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python: $PYTHON_VERSION"

if python3 -c "import torch; print(f'  PyTorch: {torch.__version__}')" 2>/dev/null; then
    if python3 -c "import torch; assert torch.cuda.is_available()" 2>/dev/null; then
        echo "  CUDA: available"
    else
        echo "  CUDA: not available (will use CPU fallback)"
    fi
else
    echo "  PyTorch: not installed (will install)"
fi

# --- 2. Install Python dependencies ---
echo ""
echo "[2/7] Installing Python dependencies..."
pip install -r requirements.txt --quiet 2>&1 | tail -1
if [ -f requirements-jetson.txt ]; then
    pip install -r requirements-jetson.txt --quiet 2>&1 | tail -1 || echo "  (Jetson deps skipped — not on Jetson)"
fi

# --- 3. Build ROS 2 workspace ---
echo ""
echo "[3/7] Building ROS 2 workspace..."
source /opt/ros/humble/setup.bash
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -5
source install/setup.bash

# --- 4. Download models ---
echo ""
echo "[4/7] Downloading models..."
bash scripts/download_models.sh

# --- 5. Initialize databases ---
echo ""
echo "[5/7] Initializing databases..."
python3 -c "
import sys
sys.path.insert(0, 'src/boxbunny_dashboard')
from boxbunny_dashboard.db.manager import DatabaseManager
db = DatabaseManager('data')
print('  Main database initialized')
# Create a demo user
db.create_user('demo', 'demo123', 'Demo User', 'individual', 'beginner')
print('  Demo user created (username: demo, password: demo123)')
"

# --- 6. Verify components ---
echo ""
echo "[6/7] Verifying components..."

echo -n "  CV model: "
if [ -f "action_prediction/model/best_model.pth" ]; then
    echo "OK"
else
    echo "MISSING (place best_model.pth in action_prediction/model/)"
fi

echo -n "  YOLO model: "
if [ -f "action_prediction/model/yolo26n-pose.pt" ]; then
    echo "OK"
else
    echo "MISSING"
fi

echo -n "  LLM model: "
if ls models/llm/*.gguf 1>/dev/null 2>&1; then
    echo "OK"
else
    echo "MISSING (run: scripts/download_models.sh)"
fi

echo -n "  Punch sequences: "
COUNT=$(ls data/punch_sequences/*.json 2>/dev/null | wc -l)
echo "$COUNT files"

echo -n "  ROS messages: "
if ros2 interface show boxbunny_msgs/msg/ConfirmedPunch 2>/dev/null | head -1 | grep -q "float64"; then
    echo "OK"
else
    echo "BUILD NEEDED"
fi

# --- 7. Summary ---
echo ""
echo "[7/7] Setup complete!"
echo ""
echo "========================================="
echo "  Quick Start:"
echo "  source install/setup.bash"
echo "  ros2 launch boxbunny_core boxbunny_dev.launch.py"
echo "========================================="
