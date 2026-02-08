#!/usr/bin/env python3
"""
RealSense Glove Tracker Node.

This module provides real-time color-based boxing glove tracking using
Intel RealSense RGB-D camera data. It detects colored gloves (green for
left, red for right), estimates their 3D positions using depth data,
and calculates approach velocities to detect punches.

Detection Pipeline:
    1. Color segmentation using HSV thresholds
    2. Contour detection and bounding box extraction
    3. Depth-based distance estimation
    4. Temporal smoothing and velocity calculation
    5. Punch detection based on distance and velocity thresholds

ROS 2 Topics:
    Subscriptions:
        - /camera/color/image_raw (Image): RGB camera stream
        - /camera/aligned_depth_to_color/image_raw (Image): Aligned depth stream
    
    Publishers:
        - glove_detections (GloveDetections): Array of detected gloves with positions
        - punch_events_raw (PunchEvent): Raw punch detection events
        - /glove_debug_image (Image): Annotated debug visualization

Parameters:
    - Color thresholds (HSV ranges for green/red detection)
    - Detection thresholds (contour area, confidence, depth)
    - Velocity parameters (approach speed, frame count)
    - Performance settings (resize scale, processing frequency)
"""

import time
from collections import deque
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from cv_bridge import CvBridge
from message_filters import Subscriber, ApproximateTimeSynchronizer
from sensor_msgs.msg import Image
from boxbunny_msgs.msg import GloveDetection, GloveDetections, PunchEvent


class GloveTracker(Node):
    """
    ROS 2 node for color-based glove tracking and punch detection.
    
    Uses HSV color segmentation to track colored boxing gloves (green=left,
    red=right) and detects punches based on approach velocity and distance
    thresholds.
    
    Attributes:
        bridge: OpenCV-ROS bridge for image conversion.
        detections_pub: Publisher for glove detection array.
        punch_pub: Publisher for raw punch events.
        debug_pub: Publisher for debug visualization.
    """
    
    def __init__(self) -> None:
        """Initialize the glove tracker node with default parameters."""
        super().__init__("glove_tracker_node")

        # ==================== Topic Configuration ====================
        self.declare_parameter("color_topic", "/camera/color/image_raw")
        self.declare_parameter("depth_topic", "/camera/aligned_depth_to_color/image_raw")
        self.declare_parameter("debug_image_topic", "/glove_debug_image")
        self.declare_parameter("punch_topic", "punch_events_raw")

        # ==================== HSV Color Thresholds ====================
        # Green glove (left hand)
        self.declare_parameter("hsv_green_lower", [45, 80, 50])
        self.declare_parameter("hsv_green_upper", [85, 255, 255])
        
        # Red glove (right hand) - requires two ranges due to HSV wrap-around
        self.declare_parameter("hsv_red_lower1", [0, 90, 50])
        self.declare_parameter("hsv_red_upper1", [10, 255, 255])
        self.declare_parameter("hsv_red_lower2", [160, 90, 50])
        self.declare_parameter("hsv_red_upper2", [180, 255, 255])

        # ==================== Detection Thresholds ====================
        self.declare_parameter("min_contour_area", 1200)
        self.declare_parameter("min_confidence", 0.3)
        self.declare_parameter("depth_threshold_m", 0.45)
        self.declare_parameter("smoothing_window", 5)
        self.declare_parameter("approach_velocity_mps", 1.5)
        self.declare_parameter("approach_frames", 3)
        self.declare_parameter("debounce_time_s", 0.5)
        self.declare_parameter("max_detection_distance_m", 2.0)

        # ==================== Depth Configuration ====================
        self.declare_parameter("depth_scale", 0.001)

        # ==================== Performance Tuning ====================
        self.declare_parameter("resize_scale", 0.7)
        self.declare_parameter("process_every_n", 2)

        # ==================== Optional Pose Verification ====================
        self.declare_parameter("use_pose_verification", False)
        self.declare_parameter("pose_model_path", "")
        self.declare_parameter("pose_min_conf", 0.25)
        self.declare_parameter("pose_process_every_n", 8)

        # Initialize image bridge
        self.bridge = CvBridge()

        # Frame processing state
        self._frame_count = 0
        self._pose_frame_count = 0
        self._last_punch_time: Dict[str, float] = {"left": 0.0, "right": 0.0}
        
        # Temporal smoothing buffers for each glove
        window_size = self.get_parameter("smoothing_window").value
        approach_frames = self.get_parameter("approach_frames").value
        
        self._distance_hist: Dict[str, deque] = {
            "left": deque(maxlen=window_size),
            "right": deque(maxlen=window_size),
        }
        self._time_hist: Dict[str, deque] = {
            "left": deque(maxlen=window_size),
            "right": deque(maxlen=window_size),
        }
        self._smoothed_hist: Dict[str, deque] = {
            "left": deque(maxlen=window_size),
            "right": deque(maxlen=window_size),
        }
        self._velocity_hist: Dict[str, deque] = {
            "left": deque(maxlen=approach_frames),
            "right": deque(maxlen=approach_frames),
        }

        # Optional pose verification
        self._pose_enabled = False
        self._pose_model = None
        self._init_pose_model()

        # Set up publishers
        self.detections_pub = self.create_publisher(GloveDetections, "glove_detections", 10)
        self.punch_pub = self.create_publisher(
            PunchEvent, self.get_parameter("punch_topic").value, 10
        )
        self.debug_pub = self.create_publisher(
            Image, self.get_parameter("debug_image_topic").value, 5
        )

        # Set up synchronized subscribers for color + depth
        self.color_sub = Subscriber(self, Image, self.get_parameter("color_topic").value)
        self.depth_sub = Subscriber(self, Image, self.get_parameter("depth_topic").value)
        self.sync = ApproximateTimeSynchronizer(
            [self.color_sub, self.depth_sub], queue_size=10, slop=0.05
        )
        self.sync.registerCallback(self._on_frames)

        # Parameter change callback
        self.add_on_set_parameters_callback(self._on_params)

        self.get_logger().info("Glove tracker node initialized")

    def _init_pose_model(self) -> None:
        """
        Initialize optional YOLO pose model for punch verification.
        
        When enabled, pose verification adds an additional check to confirm
        that a detected glove motion corresponds to an actual punching pose.
        """
        if not self.get_parameter("use_pose_verification").value:
            return
        model_path = self.get_parameter("pose_model_path").value
        if not model_path:
            self.get_logger().warn("Pose verification enabled but pose_model_path is empty")
            return
        try:
            from ultralytics import YOLO  # type: ignore

            self._pose_model = YOLO(model_path)
            self._pose_enabled = True
            self.get_logger().info("Pose verification enabled")
        except Exception as exc:  # pragma: no cover - optional
            self.get_logger().warn(f"Pose model load failed: {exc}")
            self._pose_enabled = False

    def _on_params(self, params):
        """
        Handle runtime parameter changes.
        
        Resizes history buffers when smoothing_window or approach_frames
        parameters are updated.
        
        Args:
            params: List of changed parameters.
            
        Returns:
            SetParametersResult indicating success.
        """
        for param in params:
            if param.name in ("smoothing_window", "approach_frames") and param.type_ == Parameter.Type.INTEGER:
                value = max(1, int(param.value))
                if param.name == "smoothing_window":
                    self._distance_hist["left"] = deque(self._distance_hist["left"], maxlen=value)
                    self._distance_hist["right"] = deque(self._distance_hist["right"], maxlen=value)
                    self._time_hist["left"] = deque(self._time_hist["left"], maxlen=value)
                    self._time_hist["right"] = deque(self._time_hist["right"], maxlen=value)
                    self._smoothed_hist["left"] = deque(self._smoothed_hist["left"], maxlen=value)
                    self._smoothed_hist["right"] = deque(self._smoothed_hist["right"], maxlen=value)
                else:
                    self._velocity_hist["left"] = deque(self._velocity_hist["left"], maxlen=value)
                    self._velocity_hist["right"] = deque(self._velocity_hist["right"], maxlen=value)
        return rclpy.parameter.SetParametersResult(successful=True)

    def _on_frames(self, color_msg: Image, depth_msg: Image) -> None:
        """
        Process synchronized color and depth frames.
        
        This is the main processing callback that runs the detection pipeline:
        1. Convert ROS images to OpenCV format
        2. Apply optional resizing for performance
        3. Perform color segmentation and glove detection
        4. Publish detections and debug visualization
        
        Args:
            color_msg: RGB camera image.
            depth_msg: Aligned depth image.
        """
        self._frame_count += 1
        process_every_n = int(self.get_parameter("process_every_n").value)
        if process_every_n > 1 and (self._frame_count % process_every_n) != 0:
            return

        # Convert ROS images to OpenCV format
        color = self.bridge.imgmsg_to_cv2(color_msg, desired_encoding="bgr8")
        depth = self.bridge.imgmsg_to_cv2(depth_msg)

        self._last_frame = color

        # Optional resizing for performance
        resize_scale = float(self.get_parameter("resize_scale").value)
        if resize_scale != 1.0:
            color = cv2.resize(color, None, fx=resize_scale, fy=resize_scale, interpolation=cv2.INTER_LINEAR)
            depth = cv2.resize(depth, None, fx=resize_scale, fy=resize_scale, interpolation=cv2.INTER_NEAREST)

        # Convert to HSV for color segmentation
        hsv = cv2.cvtColor(color, cv2.COLOR_BGR2HSV)

        detections = []
        debug_img = color.copy()

        # Detect each glove color
        for glove, mask in self._build_masks(hsv).items():
            det = self._detect_glove(glove, mask, depth, color.shape)
            if det:
                detections.append(det)
                self._draw_detection(debug_img, det)

        # Publish detections array
        det_msg = GloveDetections()
        det_msg.stamp = color_msg.header.stamp
        det_msg.detections = detections
        self.detections_pub.publish(det_msg)

        # Publish debug visualization
        try:
            debug_msg = self.bridge.cv2_to_imgmsg(debug_img, encoding="bgr8")
            debug_msg.header = color_msg.header
            self.debug_pub.publish(debug_msg)
            
            # Local debug window
            cv2.imshow("Glove Tracking (Green=Left, Red=Right)", debug_img)
            cv2.waitKey(1)
        except Exception:
            pass

    def _build_masks(self, hsv: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Build binary masks for each glove color using HSV thresholds.
        
        Args:
            hsv: Input image in HSV color space.
            
        Returns:
            Dictionary mapping glove names to binary masks.
        """
        # Get HSV threshold parameters
        green_lower = np.array(self.get_parameter("hsv_green_lower").value, dtype=np.uint8)
        green_upper = np.array(self.get_parameter("hsv_green_upper").value, dtype=np.uint8)

        red_lower1 = np.array(self.get_parameter("hsv_red_lower1").value, dtype=np.uint8)
        red_upper1 = np.array(self.get_parameter("hsv_red_upper1").value, dtype=np.uint8)
        red_lower2 = np.array(self.get_parameter("hsv_red_lower2").value, dtype=np.uint8)
        red_upper2 = np.array(self.get_parameter("hsv_red_upper2").value, dtype=np.uint8)

        # Create color masks
        green_mask = cv2.inRange(hsv, green_lower, green_upper)
        
        # Red requires two ranges due to HSV hue wrap-around at 180
        red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
        red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)

        # Apply morphological operations to reduce noise
        kernel = np.ones((5, 5), np.uint8)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, kernel)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)

        return {"left": green_mask, "right": red_mask}

    def _detect_glove(
        self, glove: str, mask: np.ndarray, depth: np.ndarray, shape: Tuple[int, int, int]
    ) -> Optional[GloveDetection]:
        """
        Detect a glove from a color mask and estimate its 3D position.
        
        Args:
            glove: Glove identifier ("left" or "right").
            mask: Binary mask from color segmentation.
            depth: Depth image for distance estimation.
            shape: Shape of the color image.
            
        Returns:
            GloveDetection message if a valid glove is found, None otherwise.
        """
        # Find contours in the mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # Use the largest contour (assumed to be the glove)
        contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(contour)
        min_area = float(self.get_parameter("min_contour_area").value)
        if area < min_area:
            return None

        # Get bounding box and depth ROI
        x, y, w, h = cv2.boundingRect(contour)
        roi_depth = depth[y : y + h, x : x + w]
        distance_m = self._median_depth_m(roi_depth)
        if distance_m is None:
            return None
        
        # Filter out background detections beyond max distance
        max_dist = float(self.get_parameter("max_detection_distance_m").value)
        if distance_m > max_dist:
            return None

        # Calculate confidence based on contour area
        confidence = min(1.0, area / (min_area * 3.0))

        # Apply temporal smoothing
        smoothed_distance = self._smooth_distance(glove, distance_m)
        approach_velocity = self._estimate_velocity(glove, smoothed_distance)

        # Build detection message
        det = GloveDetection()
        det.glove = glove
        det.distance_m = float(smoothed_distance)
        det.approach_velocity_mps = float(approach_velocity)
        det.confidence = float(confidence)
        det.x = int(x)
        det.y = int(y)
        det.w = int(w)
        det.h = int(h)

        # Check if this constitutes a punch
        self._maybe_publish_punch(det)

        return det

    def _median_depth_m(self, roi_depth: np.ndarray) -> Optional[float]:
        """
        Calculate median depth value from a region of interest.
        
        Args:
            roi_depth: Depth values within the bounding box.
            
        Returns:
            Median depth in meters, or None if insufficient valid pixels.
        """
        if roi_depth.size == 0:
            return None

        depth_scale = float(self.get_parameter("depth_scale").value)
        valid = roi_depth[np.where(roi_depth > 0)]
        if valid.size < 10:
            return None

        median = float(np.median(valid))
        if roi_depth.dtype == np.uint16:
            return median * depth_scale
        return median

    def _smooth_distance(self, glove: str, distance: float) -> float:
        """
        Apply temporal smoothing to distance measurements.
        
        Args:
            glove: Glove identifier.
            distance: Raw distance measurement in meters.
            
        Returns:
            Smoothed distance value.
        """
        self._distance_hist[glove].append(distance)
        self._time_hist[glove].append(time.time())
        mean_dist = float(np.mean(self._distance_hist[glove]))
        self._smoothed_hist[glove].append(mean_dist)
        return mean_dist

    def _estimate_velocity(self, glove: str, distance: float) -> float:
        """
        Estimate approach velocity from distance history.
        
        Positive velocity indicates motion toward the camera.
        
        Args:
            glove: Glove identifier.
            distance: Current smoothed distance.
            
        Returns:
            Estimated velocity in meters per second.
        """
        if len(self._smoothed_hist[glove]) < 2:
            return 0.0
            
        prev_dist = self._smoothed_hist[glove][-2]
        prev_time = self._time_hist[glove][-2]
        curr_time = self._time_hist[glove][-1]
        
        dt = curr_time - prev_time
        if dt <= 1e-4:
            return 0.0
            
        velocity = (prev_dist - distance) / dt
        self._velocity_hist[glove].append(velocity)
        return velocity

    def _maybe_publish_punch(self, det: GloveDetection) -> None:
        """
        Check detection against punch criteria and publish if valid.
        
        A punch is detected when:
        1. Glove confidence exceeds threshold
        2. Debounce period has elapsed since last punch
        3. Glove is within depth threshold AND approaching fast enough,
           OR glove is very close (< 0.35m)
        
        Args:
            det: Current glove detection to evaluate.
        """
        now = time.time()
        min_conf = float(self.get_parameter("min_confidence").value)
        if det.confidence < min_conf:
            return

        debounce = float(self.get_parameter("debounce_time_s").value)
        if now - self._last_punch_time[det.glove] < debounce:
            return

        depth_threshold = float(self.get_parameter("depth_threshold_m").value)
        approach_velocity = float(self.get_parameter("approach_velocity_mps").value)
        approach_frames = int(self.get_parameter("approach_frames").value)

        velocity_hits = sum(1 for v in self._velocity_hist[det.glove] if v > approach_velocity)
        velocity_ok = velocity_hits >= approach_frames
        distance_ok = det.distance_m <= depth_threshold

        pose_ok = self._verify_pose() if self.get_parameter("use_pose_verification").value else True

        # Trigger punch if close AND approaching fast, OR just very close (under 0.35m)
        very_close = det.distance_m <= 0.35
        if ((velocity_ok and distance_ok) or very_close) and pose_ok:
            self._last_punch_time[det.glove] = now
            event = PunchEvent()
            event.stamp = self.get_clock().now().to_msg()
            event.glove = det.glove
            event.distance_m = det.distance_m
            event.approach_velocity_mps = det.approach_velocity_mps
            event.confidence = det.confidence
            event.method = "velocity" if velocity_ok else "threshold"
            event.is_punch = True
            event.punch_type = "unknown"
            event.imu_confirmed = False
            event.source = "vision"
            self.punch_pub.publish(event)

    def _verify_pose(self) -> bool:
        """
        Verify punch detection using pose estimation (optional).
        
        When enabled, checks that a person with high-confidence keypoints
        is detected in the frame. This helps filter out false positives
        from non-human colored objects.
        
        Returns:
            True if pose verification passes or is disabled.
        """
        if not self._pose_enabled or self._pose_model is None:
            return True

        self._pose_frame_count += 1
        if (self._pose_frame_count % int(self.get_parameter("pose_process_every_n").value)) != 0:
            return True

        try:
            result = self._pose_model(self._last_frame, verbose=False) if hasattr(self, "_last_frame") else None
            if not result or len(result) == 0:
                return False
            kps = result[0].keypoints
            if kps is None or kps.conf is None:
                return False
            return bool(np.max(kps.conf) >= float(self.get_parameter("pose_min_conf").value))
        except Exception:
            return True

    def _draw_detection(self, img: np.ndarray, det: GloveDetection) -> None:
        """
        Draw detection visualization on debug image.
        
        Args:
            img: Image to draw on (modified in place).
            det: Detection to visualize.
        """
        # Green for left glove, red for right glove
        color = (0, 255, 0) if det.glove == "left" else (0, 0, 255)
        cv2.rectangle(img, (det.x, det.y), (det.x + det.w, det.y + det.h), color, 2)
        label = f"{det.glove} {det.distance_m:.2f}m v={det.approach_velocity_mps:.2f}"
        cv2.putText(img, label, (det.x, max(det.y - 6, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)


def main() -> None:
    """Entry point for the glove tracker node."""
    rclpy.init()
    node = GloveTracker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
