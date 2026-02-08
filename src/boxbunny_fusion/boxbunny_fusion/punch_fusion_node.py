#!/usr/bin/env python3
"""
Punch Fusion Node.

This module provides sensor fusion for punch detection by combining
vision-based punch detections with IMU (Inertial Measurement Unit)
confirmations. The fusion approach improves punch classification accuracy
by correlating visual detections with accelerometer/gyroscope data.

Fusion Logic:
    - When IMU confirmation is required and available: Combines vision
      detection with IMU punch type classification.
    - When IMU is unavailable but vision fallback is allowed: Uses
      vision-only detection with reduced confidence.

ROS 2 Topics:
    Subscriptions:
        - punch_events_raw (PunchEvent): Raw vision-based punch detections
        - imu/punch (ImuPunch): IMU-based punch classifications
    
    Publishers:
        - punch_events (PunchEvent): Fused punch events with confirmed types

Parameters:
    - vision_topic (str): Input topic for vision detections (default: "punch_events_raw")
    - imu_topic (str): Input topic for IMU punch data (default: "imu/punch")
    - output_topic (str): Output topic for fused events (default: "punch_events")
    - fusion_window_s (float): Time window for correlating vision/IMU events (default: 0.25)
    - require_imu_confirmation (bool): Require IMU data for output (default: True)
    - allow_vision_fallback (bool): Allow vision-only when IMU unavailable (default: True)
"""

import time
from typing import Optional

import rclpy
from rclpy.node import Node
from boxbunny_msgs.msg import PunchEvent, ImuPunch


class PunchFusionNode(Node):
    """
    ROS 2 node for fusing vision and IMU punch detection data.
    
    This node correlates vision-based punch detections with IMU
    classifications to produce high-confidence, typed punch events.
    
    Attributes:
        _last_imu: Most recent IMU punch message.
        _last_imu_time: Timestamp of the last IMU message.
        pub: Publisher for fused punch events.
    """
    
    def __init__(self) -> None:
        """Initialize the punch fusion node with default parameters."""
        super().__init__("punch_fusion_node")

        # Declare ROS parameters
        self.declare_parameter("vision_topic", "punch_events_raw")
        self.declare_parameter("imu_topic", "imu/punch")
        self.declare_parameter("output_topic", "punch_events")
        self.declare_parameter("fusion_window_s", 0.25)
        self.declare_parameter("require_imu_confirmation", True)
        self.declare_parameter("allow_vision_fallback", True)

        # Get topic configurations
        vision_topic = self.get_parameter("vision_topic").value
        imu_topic = self.get_parameter("imu_topic").value
        output_topic = self.get_parameter("output_topic").value

        # Initialize state for temporal correlation
        self._last_imu: Optional[ImuPunch] = None
        self._last_imu_time = 0.0

        # Set up ROS subscriptions and publisher
        self.create_subscription(PunchEvent, vision_topic, self._on_vision_punch, 10)
        self.create_subscription(ImuPunch, imu_topic, self._on_imu_punch, 10)
        self.pub = self.create_publisher(PunchEvent, output_topic, 10)

        self.get_logger().info(
            f"Punch fusion node initialized - "
            f"fusing '{vision_topic}' with '{imu_topic}'"
        )

    def _on_imu_punch(self, msg: ImuPunch) -> None:
        """
        Handle incoming IMU punch classification.
        
        Stores the latest IMU punch data for correlation with
        subsequent vision detections.
        
        Args:
            msg: The IMU punch classification message.
        """
        self._last_imu = msg
        self._last_imu_time = time.time()

    def _on_vision_punch(self, msg: PunchEvent) -> None:
        """
        Handle incoming vision-based punch detection.
        
        Attempts to correlate the vision detection with recent IMU data
        to produce a fused punch event with accurate type classification.
        
        Args:
            msg: The vision-based punch detection message.
        """
        require_imu = bool(self.get_parameter("require_imu_confirmation").value)
        allow_vision = bool(self.get_parameter("allow_vision_fallback").value)
        window_s = float(self.get_parameter("fusion_window_s").value)

        # Check if we have recent IMU data within the fusion window
        imu = self._last_imu
        has_imu = imu is not None and (time.time() - self._last_imu_time) <= window_s

        # Skip if IMU is required but unavailable and no fallback allowed
        if not has_imu and require_imu and not allow_vision:
            return

        # Build fused punch event
        fused = PunchEvent()
        fused.stamp = msg.stamp
        fused.glove = msg.glove
        fused.distance_m = msg.distance_m
        fused.approach_velocity_mps = msg.approach_velocity_mps
        fused.confidence = msg.confidence
        fused.method = msg.method
        fused.is_punch = msg.is_punch

        if has_imu and imu is not None:
            # Fused detection: combine vision with IMU classification
            fused.source = "vision+imu"
            fused.punch_type = self._classify_punch_type(imu.punch_type, msg.glove)
            fused.imu_confirmed = True
        else:
            # Vision-only fallback
            fused.source = "vision"
            fused.punch_type = "unknown"
            fused.imu_confirmed = False

        self.pub.publish(fused)

    def _classify_punch_type(self, punch_type: str, glove: str) -> str:
        """
        Map IMU punch classification to specific punch type based on glove side.
        
        Args:
            punch_type: Raw punch type from IMU (e.g., "straight", "hook").
            glove: Which glove detected the punch ("left" or "right").
            
        Returns:
            Specific punch type name (e.g., "jab", "cross", "left_hook").
        """
        # Map straight punches to jab/cross based on hand
        if punch_type == "straight":
            return "jab" if glove == "left" else "cross"
        
        # Prefix hooks and uppercuts with hand side
        if punch_type in {"hook", "uppercut"}:
            side = "left" if glove == "left" else "right"
            return f"{side}_{punch_type}"
        
        return punch_type or "unknown"


def main() -> None:
    """Entry point for the punch fusion node."""
    rclpy.init()
    node = PunchFusionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
