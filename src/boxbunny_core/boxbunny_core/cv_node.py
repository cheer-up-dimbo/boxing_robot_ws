"""Computer vision node for BoxBunny.

Wraps the action_prediction/lib/inference_runtime.InferenceEngine to provide
real-time punch detection, pose estimation, and user tracking via ROS 2 topics.
Subscribes to RealSense RGB+depth streams, publishes detections.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String

from boxbunny_msgs.msg import PoseEstimate, PunchDetection, SessionState, UserTracking
from boxbunny_core.constants import Topics

logger = logging.getLogger("boxbunny.cv_node")

# Add action_prediction to path
_WS_ROOT = Path(__file__).resolve().parents[3]
_AP_ROOT = _WS_ROOT / "action_prediction"
if str(_AP_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(_AP_ROOT.parent))


class CvNode(Node):
    """ROS 2 node wrapping the action prediction inference engine."""

    def __init__(self) -> None:
        super().__init__("cv_node")

        # Parameters
        self.declare_parameter("checkpoint_path",
                               str(_AP_ROOT / "model" / "best_model.pth"))
        self.declare_parameter("yolo_model_path",
                               str(_AP_ROOT / "model" / "yolo26n-pose.pt"))
        self.declare_parameter("device", "cuda:0")
        self.declare_parameter("inference_interval", 1)
        self.declare_parameter("window_size", 12)
        self.declare_parameter("enabled", True)
        self.declare_parameter("debug_mode", True)

        self._checkpoint_path = self.get_parameter("checkpoint_path").value
        self._yolo_model_path = self.get_parameter("yolo_model_path").value
        self._device = self.get_parameter("device").value
        self._inference_interval = self.get_parameter("inference_interval").value
        self._window_size = self.get_parameter("window_size").value
        self._enabled = self.get_parameter("enabled").value
        self._debug_mode = self.get_parameter("debug_mode").value

        # State
        self._engine = None
        self._initialized = False
        self._frame_count = 0
        self._session_active = False
        self._bridge = CvBridge()
        self._latest_rgb: Optional[np.ndarray] = None
        self._latest_depth: Optional[np.ndarray] = None
        self._last_bbox: Optional[dict] = None
        self._baseline_bbox_x: Optional[float] = None
        self._baseline_depth: Optional[float] = None

        # Subscribers
        self.create_subscription(
            Image, Topics.CAMERA_COLOR, self._on_color, 5
        )
        self.create_subscription(
            Image, Topics.CAMERA_DEPTH, self._on_depth, 5
        )
        self.create_subscription(
            SessionState, Topics.SESSION_STATE, self._on_session_state, 10
        )

        # Publishers
        self._pub_detection = self.create_publisher(
            PunchDetection, Topics.CV_DETECTION, 10
        )
        self._pub_pose = self.create_publisher(
            PoseEstimate, Topics.CV_POSE, 10
        )
        self._pub_tracking = self.create_publisher(
            UserTracking, Topics.CV_USER_TRACKING, 10
        )
        self._pub_debug_info = self.create_publisher(
            String, Topics.CV_DEBUG_INFO, 10
        )
        self._pub_person_direction = self.create_publisher(
            String, Topics.CV_PERSON_DIRECTION, 10
        )
        self._last_direction: str = "centre"
        self._frame_width: float = 960.0  # default, updated from first frame

        # Inference timer (runs at camera rate when active)
        self.create_timer(1.0 / 30.0, self._inference_tick)

        logger.info("CV node initialized (checkpoint=%s, device=%s, debug=%s)",
                     self._checkpoint_path, self._device, self._debug_mode)

    def _lazy_init(self) -> bool:
        """Lazy-load the inference engine on first use."""
        if self._initialized:
            return True
        if not self._enabled:
            return False
        try:
            from action_prediction.lib.inference_runtime import InferenceEngine
            self._engine = InferenceEngine(
                checkpoint_path=self._checkpoint_path,
                yolo_model_path=self._yolo_model_path,
                device=self._device,
                window_size=self._window_size,
            )
            self._engine.initialize()
            self._initialized = True
            logger.info("Inference engine loaded successfully")
            return True
        except Exception as e:
            logger.error("Failed to load inference engine: %s", e)
            self._enabled = False
            return False

    def _on_color(self, msg: Image) -> None:
        """Receive RGB frame from RealSense."""
        try:
            self._latest_rgb = self._bridge.imgmsg_to_cv2(msg, "bgr8")
            if self._latest_rgb is not None:
                self._frame_width = float(self._latest_rgb.shape[1])
        except Exception as e:
            logger.debug("Color frame decode error: %s", e)

    def _on_depth(self, msg: Image) -> None:
        """Receive depth frame from RealSense."""
        try:
            self._latest_depth = self._bridge.imgmsg_to_cv2(msg, "passthrough")
        except Exception as e:
            logger.debug("Depth frame decode error: %s", e)

    def _on_session_state(self, msg: SessionState) -> None:
        """Track session state for baseline management."""
        was_active = self._session_active
        self._session_active = msg.state in ("countdown", "active", "rest")
        if self._session_active and not was_active:
            self._baseline_bbox_x = None
            self._baseline_depth = None

    def _inference_tick(self) -> None:
        """Run inference on the latest frame pair."""
        if self._latest_rgb is None or self._latest_depth is None:
            return
        if not self._enabled:
            return

        self._frame_count += 1
        if self._frame_count % self._inference_interval != 0:
            return

        # Initialize on first frame (not gated by session state)
        if not self._lazy_init():
            return

        rgb = self._latest_rgb
        depth = self._latest_depth

        try:
            result = self._engine.process_frame(rgb, depth)
        except Exception as e:
            logger.error("Inference error: %s", e)
            return

        if result is None:
            return

        now = time.time()

        # Publish punch detection with consecutive frame count
        det_msg = PunchDetection()
        det_msg.timestamp = now
        det_msg.punch_type = result.action
        det_msg.confidence = result.confidence
        det_msg.raw_class = result.raw_action
        det_msg.consecutive_frames = result.consecutive_frames
        self._pub_detection.publish(det_msg)

        # Publish pose estimate (keypoints + movement delta)
        self._publish_pose(result, now)

        # Publish user tracking (from YOLO pose bbox)
        self._publish_tracking(result, now)

        # Publish debug info (lightweight text, no video)
        if self._debug_mode:
            self._publish_debug_info(result)

    def _publish_pose(self, result, timestamp: float) -> None:
        """Publish pose keypoints and movement delta."""
        if result.keypoints is None:
            return
        msg = PoseEstimate()
        msg.timestamp = timestamp
        try:
            msg.keypoints = list(result.keypoints.flatten().astype(float))
        except Exception:
            return
        msg.movement_delta = float(result.movement_delta)
        self._pub_pose.publish(msg)

    def _publish_tracking(self, result, timestamp: float) -> None:
        """Publish user tracking data from inference result."""
        tracking = UserTracking()
        tracking.timestamp = timestamp

        bbox = result.bbox
        if bbox is None:
            tracking.user_detected = False
            self._pub_tracking.publish(tracking)
            return

        tracking.user_detected = True
        tracking.bbox_centre_x = bbox.get("cx", 0.0)
        tracking.bbox_centre_y = bbox.get("cy", 0.0)
        tracking.bbox_top_y = bbox.get("top_y", 0.0)
        tracking.bbox_width = bbox.get("width", 0.0)
        tracking.bbox_height = bbox.get("height", 0.0)
        tracking.depth = bbox.get("depth", 0.0)

        # Compute displacement from baseline
        if self._baseline_bbox_x is None and tracking.user_detected:
            self._baseline_bbox_x = tracking.bbox_centre_x
            self._baseline_depth = tracking.depth

        if self._baseline_bbox_x is not None:
            tracking.lateral_displacement = tracking.bbox_centre_x - self._baseline_bbox_x
        if self._baseline_depth is not None:
            tracking.depth_displacement = tracking.depth - self._baseline_depth

        self._pub_tracking.publish(tracking)

        # Publish person direction for yaw motor tracking
        if tracking.user_detected:
            self._publish_person_direction(tracking.bbox_centre_x)

    def _publish_person_direction(self, cx: float) -> None:
        """Publish left/right/centre based on bbox position with hysteresis."""
        w = self._frame_width
        # Centre zone = middle 30% of frame
        left_boundary = w * 0.35
        right_boundary = w * 0.65
        hysteresis = 20.0  # px past boundary before switching

        if self._last_direction == "centre":
            if cx < left_boundary - hysteresis:
                new_dir = "left"
            elif cx > right_boundary + hysteresis:
                new_dir = "right"
            else:
                new_dir = "centre"
        elif self._last_direction == "left":
            if cx > left_boundary + hysteresis:
                new_dir = "centre" if cx <= right_boundary else "right"
            else:
                new_dir = "left"
        elif self._last_direction == "right":
            if cx < right_boundary - hysteresis:
                new_dir = "centre" if cx >= left_boundary else "left"
            else:
                new_dir = "right"
        else:
            new_dir = "centre"

        if new_dir != self._last_direction:
            self._last_direction = new_dir
            msg = String()
            msg.data = new_dir
            self._pub_person_direction.publish(msg)

    def _publish_debug_info(self, result) -> None:
        """Publish lightweight detection metadata for debug panel."""
        msg = String()
        msg.data = json.dumps({
            "action": result.action,
            "confidence": round(result.confidence, 3),
            "consecutive": result.consecutive_frames,
            "raw": result.raw_action,
            "fps": round(result.fps, 1),
            "movement_delta": round(result.movement_delta, 1),
        })
        self._pub_debug_info.publish(msg)


def main(args=None) -> None:
    """Entry point for the CV node."""
    rclpy.init(args=args)
    node = CvNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
