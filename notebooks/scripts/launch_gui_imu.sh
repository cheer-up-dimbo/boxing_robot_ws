#!/usr/bin/env bash
# Launch both the BoxBunny GUI and the IMU Simulator side by side.
# Press Ctrl+C or notebook STOP to close both.
cd /home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws
source /opt/ros/humble/setup.bash && source install/setup.bash

export QT_QPA_PLATFORM=xcb
export QT_QPA_PLATFORM_PLUGIN_PATH=$(python3 -c "import PySide6; print(PySide6.__path__[0])")/Qt/plugins/platforms
unset QT_PLUGIN_PATH

GUI_PID=""
IMU_PID=""

cleanup() {
    echo ""
    echo "=== Closing all windows ==="
    [ -n "$GUI_PID" ] && kill $GUI_PID 2>/dev/null
    [ -n "$IMU_PID" ] && kill $IMU_PID 2>/dev/null
    sleep 0.5
    [ -n "$GUI_PID" ] && kill -9 $GUI_PID 2>/dev/null
    [ -n "$IMU_PID" ] && kill -9 $IMU_PID 2>/dev/null
    echo "All windows closed."
}
trap cleanup EXIT INT TERM

echo "Launching BoxBunny GUI + IMU Simulator..."
echo "Click IMU pads to control the GUI."
echo "Press STOP (interrupt) to close both."
echo ""

python3 -c "
import sys, os, signal
sys.path.insert(0, 'src/boxbunny_gui')
os.environ.pop('QT_PLUGIN_PATH', None)
from boxbunny_gui.app import BoxBunnyApp
app = BoxBunnyApp()
def _shutdown(sig, frame):
    try: app._window.close()
    except: pass
    sys.exit(0)
signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)
app.run()
" 2>&1 &
GUI_PID=$!
echo "GUI started (PID=$GUI_PID)"

sleep 2

python3 tools/imu_simulator.py 2>&1 &
IMU_PID=$!
echo "IMU Simulator started (PID=$IMU_PID)"

echo ""
echo "=== Both windows running — Press STOP to close ==="

wait -n $GUI_PID $IMU_PID 2>/dev/null || wait $GUI_PID
