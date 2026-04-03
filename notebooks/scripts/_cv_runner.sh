#!/bin/bash
set +e
eval "$(conda shell.bash hook 2>/dev/null)"
conda activate boxing_ai 2>/dev/null || true
export DISPLAY="${DISPLAY:-:0}"
WS="/home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws"
cd "$WS/action_prediction"
echo "=== CV Model Running ==="
echo "Predictions shown here. Close this window to stop CV."
echo ""
python3 run.py
