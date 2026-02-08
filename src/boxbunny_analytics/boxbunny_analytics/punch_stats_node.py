#!/usr/bin/env python3
"""
Punch Statistics Node.

This module provides real-time punch statistics aggregation and publishing
for the BoxBunny boxing training system. It collects punch events within
a sliding time window and computes statistics including punch counts by type,
average velocity, confidence scores, and IMU confirmation ratios.

ROS 2 Topics:
    Subscriptions:
        - punch_events (PunchEvent): Incoming punch detection events
    
    Publishers:
        - punch_stats (String): JSON-encoded statistics summary

Parameters:
    - punch_topic (str): Topic name for incoming punch events (default: "punch_events")
    - output_topic (str): Topic name for statistics output (default: "punch_stats")
    - window_s (float): Sliding window duration in seconds (default: 30.0)
    - publish_period_s (float): Statistics publishing interval (default: 2.0)
"""

import json
import time
from collections import deque
from typing import Deque, Dict, Tuple

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from boxbunny_msgs.msg import PunchEvent


class PunchStatsNode(Node):
    """
    ROS 2 node for aggregating and publishing punch statistics.
    
    This node maintains a sliding window of recent punch events and periodically
    publishes aggregated statistics including punch counts, average velocity,
    and IMU confirmation ratios.
    
    Attributes:
        _window: Deque storing timestamped punch events within the sliding window.
        sub: Subscription to punch events.
        pub: Publisher for statistics output.
        timer: Timer for periodic statistics publishing.
    """
    
    def __init__(self) -> None:
        """Initialize the punch statistics node with default parameters."""
        super().__init__("punch_stats_node")

        # Declare ROS parameters with defaults
        self.declare_parameter("punch_topic", "punch_events")
        self.declare_parameter("output_topic", "punch_stats")
        self.declare_parameter("window_s", 30.0)
        self.declare_parameter("publish_period_s", 2.0)

        # Initialize sliding window buffer for punch events
        # maxlen prevents unbounded memory growth
        self._window: Deque[Tuple[float, PunchEvent]] = deque(maxlen=3000)

        # Get configured topic names
        punch_topic = self.get_parameter("punch_topic").value
        output_topic = self.get_parameter("output_topic").value

        # Set up ROS communication
        self.sub = self.create_subscription(PunchEvent, punch_topic, self._on_punch, 10)
        self.pub = self.create_publisher(String, output_topic, 10)
        self.timer = self.create_timer(
            float(self.get_parameter("publish_period_s").value), 
            self._publish_stats
        )

        self.get_logger().info(
            f"Punch statistics node initialized - "
            f"listening on '{punch_topic}', publishing to '{output_topic}'"
        )

    def _on_punch(self, msg: PunchEvent) -> None:
        """
        Handle incoming punch event messages.
        
        Args:
            msg: The punch event message containing detection details.
        """
        stamp = self._to_sec(msg.stamp)
        self._window.append((stamp, msg))

    def _publish_stats(self) -> None:
        """
        Compute and publish aggregated punch statistics.
        
        Removes expired events from the sliding window, computes statistics
        over remaining events, and publishes a JSON-encoded summary.
        """
        window_s = float(self.get_parameter("window_s").value)
        now = time.time()
        
        # Remove expired events from the sliding window
        while self._window and now - self._window[0][0] > window_s:
            self._window.popleft()

        # Initialize statistics accumulators
        counts: Dict[str, int] = {}
        total = 0
        avg_velocity = 0.0
        avg_confidence = 0.0
        imu_confirmed = 0

        # Aggregate statistics over all events in window
        for _, msg in self._window:
            total += 1
            ptype = msg.punch_type or "unknown"
            counts[ptype] = counts.get(ptype, 0) + 1
            avg_velocity += msg.approach_velocity_mps
            avg_confidence += msg.confidence
            if msg.imu_confirmed:
                imu_confirmed += 1

        # Compute averages (avoid division by zero)
        if total > 0:
            avg_velocity /= total
            avg_confidence /= total

        # Build statistics summary
        summary = {
            "window_s": window_s,
            "total": total,
            "counts": counts,
            "avg_velocity_mps": round(avg_velocity, 3),
            "avg_confidence": round(avg_confidence, 3),
            "imu_confirmed_ratio": round((imu_confirmed / total) if total > 0 else 0.0, 3),
        }

        # Publish JSON-encoded statistics
        out = String()
        out.data = json.dumps(summary)
        self.pub.publish(out)

    @staticmethod
    def _to_sec(stamp) -> float:
        """
        Convert a ROS timestamp to seconds as a float.
        
        Args:
            stamp: A ROS Time message with sec and nanosec fields.
            
        Returns:
            The timestamp as a floating-point number in seconds.
        """
        return float(stamp.sec) + float(stamp.nanosec) * 1e-9


def main() -> None:
    """Entry point for the punch statistics node."""
    rclpy.init()
    node = PunchStatsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
