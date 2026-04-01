#!/usr/bin/env bash
# Launch the main BoxBunny touchscreen GUI for visual inspection.
# Close the window to end.
cd /home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws
source /opt/ros/humble/setup.bash && source install/setup.bash

export QT_QPA_PLATFORM=xcb
export QT_QPA_PLATFORM_PLUGIN_PATH=$(python3 -c "import PySide6; print(PySide6.__path__[0])")/Qt/plugins/platforms
unset QT_PLUGIN_PATH

echo "Launching BoxBunny GUI..."
echo "Close the window to end the test."
echo ""

python3 -c "
import sys, os, signal
sys.path.insert(0, 'src/boxbunny_gui')
os.environ.pop('QT_PLUGIN_PATH', None)

from boxbunny_gui.app import BoxBunnyApp
app = BoxBunnyApp()

def _shutdown(sig, frame):
    try:
        app._window.close()
    except Exception:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)

app.run()
" 2>&1 || true
