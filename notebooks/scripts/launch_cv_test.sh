#!/usr/bin/env bash
# Run the CV action prediction model with live camera feed.
set +e
cd /home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws
source /opt/ros/humble/setup.bash && source install/setup.bash
python3 action_prediction/run.py \
    --checkpoint action_prediction/model/best_model.pth \
    --pose-weights action_prediction/model/yolo26n-pose.pt \
    2>&1 || echo "(D435i camera not connected or models missing)"
