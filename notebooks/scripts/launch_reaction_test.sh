#!/usr/bin/env bash
# Reaction Time Test — YOLO pose estimation with live camera.
# Opens a camera window showing pose skeleton overlay.
# Detects motion (keypoint displacement > 20px) and prints reaction time.
#
# This tests the same pipeline the GUI reaction test page uses:
#   RealSense/webcam → YOLO pose → keypoint tracking → motion detection
#
# Press 'q' to stop.
set +e

WS="/home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws"
cd "$WS"

echo "=== Reaction Time / Pose Estimation Test ==="
echo "Stand 1.5-2m from the camera."
echo "When you see GREEN, punch as fast as you can."
echo "Press 'q' to quit."
echo ""

python3 << 'PYEOF'
import sys
import time
import random
from pathlib import Path

import cv2
import numpy as np

WS = Path("/home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws")
YOLO_PATH = WS / "action_prediction" / "model" / "yolo26n-pose.pt"
MOTION_THRESHOLD = 20.0  # pixels

# Try loading YOLO
try:
    from ultralytics import YOLO
except ImportError:
    print("ERROR: ultralytics not installed. Run: pip install ultralytics")
    sys.exit(1)

model_path = str(YOLO_PATH) if YOLO_PATH.exists() else "yolo11s-pose.pt"
print(f"Loading YOLO pose model: {model_path}")
model = YOLO(model_path)

# Try RealSense first, fall back to webcam
cap = None
try:
    import pyrealsense2 as rs
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    pipeline.start(config)
    print("Camera: RealSense D435i")
    use_rs = True
except Exception:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: No camera available")
        sys.exit(1)
    print("Camera: Webcam (fallback)")
    use_rs = False

# Warmup
print("Warming up (5 frames)...")
for _ in range(5):
    if use_rs:
        frames = pipeline.wait_for_frames()
        bgr = np.asanyarray(frames.get_color_frame().get_data())
    else:
        _, bgr = cap.read()
        bgr = cv2.flip(bgr, 1)
    model(bgr, verbose=False)
print("Ready!\n")

# State machine
STATE_WAIT = "wait"
STATE_RED = "red"
STATE_GREEN = "green"
STATE_RESULT = "result"

state = STATE_WAIT
prev_kps = None
trial = 0
results = []
stimulus_time = 0.0
delay_until = 0.0

def extract_kps(res):
    if not res or len(res) == 0:
        return None
    kps = res[0].keypoints
    if kps is None or kps.data is None:
        return None
    arr = kps.data.cpu().numpy()
    return arr[0] if arr.shape[0] > 0 else None

def draw_skeleton(img, kps):
    if kps is None:
        return
    for i in range(len(kps)):
        x, y = int(kps[i][0]), int(kps[i][1])
        conf = kps[i][2] if len(kps[i]) >= 3 else 1.0
        if conf > 0.3:
            cv2.circle(img, (x, y), 5, (0, 255, 0), -1)

def compute_motion(prev, curr):
    if prev is None or curr is None:
        return 0.0
    max_d = 0.0
    for i in range(min(len(prev), len(curr))):
        if len(prev[i]) >= 3 and prev[i][2] < 0.3:
            continue
        if len(curr[i]) >= 3 and curr[i][2] < 0.3:
            continue
        d = float(np.sqrt((curr[i][0]-prev[i][0])**2 + (curr[i][1]-prev[i][1])**2))
        max_d = max(max_d, d)
    return max_d

print("Press SPACE to start a trial. Press 'q' to quit.\n")

while True:
    if use_rs:
        frames = pipeline.wait_for_frames()
        bgr = np.asanyarray(frames.get_color_frame().get_data())
    else:
        ok, bgr = cap.read()
        if not ok:
            break
        bgr = cv2.flip(bgr, 1)

    display = bgr.copy()
    h, w = display.shape[:2]

    # Run pose
    res = model(bgr, verbose=False)
    kps = extract_kps(res)
    draw_skeleton(display, kps)

    now = time.time()

    if state == STATE_WAIT:
        cv2.putText(display, "Press SPACE to start", (w//2-180, h//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2)
        if trial > 0:
            cv2.putText(display, f"Trial {trial}: {results[-1]:.0f}ms",
                        (w//2-140, h//2+50), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 165, 255), 2)

    elif state == STATE_RED:
        cv2.rectangle(display, (0, 0), (w, h), (0, 0, 180), -1)
        cv2.putText(display, "WAIT...", (w//2-100, h//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        if now >= delay_until:
            state = STATE_GREEN
            stimulus_time = time.time()
            prev_kps = kps  # baseline

    elif state == STATE_GREEN:
        cv2.rectangle(display, (0, 0), (w, h), (0, 180, 0), -1)
        cv2.putText(display, "PUNCH NOW!", (w//2-160, h//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        motion = compute_motion(prev_kps, kps)
        if motion > MOTION_THRESHOLD:
            reaction_ms = (time.time() - stimulus_time) * 1000
            results.append(reaction_ms)
            trial += 1
            state = STATE_RESULT
            print(f"  Trial {trial}: {reaction_ms:.0f} ms  (motion: {motion:.1f}px)")
        prev_kps = kps

    elif state == STATE_RESULT:
        color = (0, 255, 0) if results[-1] < 250 else (0, 165, 255)
        cv2.putText(display, f"{results[-1]:.0f} ms", (w//2-100, h//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, color, 3)
        cv2.putText(display, "SPACE for next | Q to quit", (w//2-200, h//2+60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    # Stats bar
    if results:
        avg = sum(results) / len(results)
        best = min(results)
        cv2.putText(display, f"Avg: {avg:.0f}ms  Best: {best:.0f}ms  Trials: {len(results)}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)

    cv2.imshow("Reaction Time Test", display)
    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        break
    elif key == ord(' '):
        if state in (STATE_WAIT, STATE_RESULT):
            state = STATE_RED
            delay_until = time.time() + random.uniform(1.0, 3.5)
            prev_kps = None

# Cleanup
cv2.destroyAllWindows()
if use_rs:
    pipeline.stop()
else:
    cap.release()

if results:
    print(f"\n=== Results ({len(results)} trials) ===")
    print(f"  Average: {sum(results)/len(results):.0f} ms")
    print(f"  Best:    {min(results):.0f} ms")
    print(f"  Worst:   {max(results):.0f} ms")
else:
    print("\nNo trials completed.")
PYEOF

echo ""
echo "=== Test Complete ==="
