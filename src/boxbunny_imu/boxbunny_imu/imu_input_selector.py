#!/usr/bin/env python3
"""
IMU Input Selector Node.

This module enables gesture-based menu navigation by converting IMU punch
classifications into numeric menu selections. This allows users to interact
with the boxing training system using punches instead of traditional input
devices.

Punch-to-Selection Mapping:
    - Jab (straight left) -> Selection 1
    - Cross (straight right) -> Selection 2
    - Left Hook -> Selection 3
    - Right Hook -> Selection 4
    - Left Uppercut -> Selection 5
    - Right Uppercut -> Selection 6

ROS 2 Topics:
    Subscriptions:
        - imu/punch (ImuPunch): Classified punch events from IMU
    
    Publishers:
        - imu_selection (Int32): Numeric selection corresponding to punch type
        - imu_input_enabled (Bool): Current enabled state of IMU input

Services:
    - imu_input_selector/enable (SetBool): Enable/disable IMU input mode

Parameters:
    - enabled (bool): Initial enabled state (default: False)
    - confidence_threshold (float): Minimum confidence for punch acceptance (default: 0.7)
    - cooldown_s (float): Minimum time between selections in seconds (default: 1.0)
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32, Bool
from std_srvs.srv import SetBool
from boxbunny_msgs.msg import ImuPunch


class ImuInputSelector(Node):
    """
    ROS 2 node that maps IMU punch events to menu selections.
    
    This node enables punch-based navigation by converting classified
    punch types to numeric selections. A cooldown prevents accidental
    rapid selections.
    
    Attributes:
        enabled: Whether punch-to-selection conversion is active.
        confidence_threshold: Minimum punch confidence for acceptance.
        cooldown: Minimum time between consecutive selections.
        last_selection_time: Timestamp of the most recent selection.
    """
    
    # Mapping from punch types to menu selection numbers
    PUNCH_TO_SELECTION = {
        'jab': 1,
        'cross': 2,
        'left_hook': 3,
        'right_hook': 4,
        'left_uppercut': 5,
        'right_uppercut': 6,
    }
    
    def __init__(self) -> None:
        """Initialize the IMU input selector node."""
        super().__init__('imu_input_selector')
        
        # Declare ROS parameters
        self.declare_parameter('enabled', False)
        self.declare_parameter('confidence_threshold', 0.7)
        self.declare_parameter('cooldown_s', 1.0)
        
        # Cache parameter values for performance
        self.enabled = self.get_parameter('enabled').value
        self.confidence_threshold = self.get_parameter('confidence_threshold').value
        self.cooldown = self.get_parameter('cooldown_s').value
        
        # Initialize state
        self.last_selection_time = 0.0
        
        # Set up publishers
        self.selection_pub = self.create_publisher(Int32, 'imu_selection', 10)
        self.enabled_pub = self.create_publisher(Bool, 'imu_input_enabled', 10)
        
        # Set up subscription
        self.punch_sub = self.create_subscription(
            ImuPunch, 'imu/punch', self._on_punch, 10
        )
        
        # Set up service
        self.enable_srv = self.create_service(
            SetBool, 'imu_input_selector/enable', self._handle_enable
        )
        
        # Publish initial enabled state
        self._publish_enabled_state()
        
        self.get_logger().info(
            f"IMU input selector initialized (enabled={self.enabled})"
        )
    
    def _handle_enable(self, request, response):
        """
        Handle enable/disable service requests.
        
        Args:
            request: SetBool request with desired enabled state.
            response: SetBool response to populate.
            
        Returns:
            Populated response indicating success.
        """
        self.enabled = request.data
        self._publish_enabled_state()
        
        response.success = True
        response.message = f"IMU input {'enabled' if self.enabled else 'disabled'}"
        self.get_logger().info(response.message)
        
        return response
    
    def _publish_enabled_state(self) -> None:
        """Publish the current enabled state for UI synchronization."""
        msg = Bool()
        msg.data = self.enabled
        self.enabled_pub.publish(msg)
    
    def _on_punch(self, msg: ImuPunch) -> None:
        """
        Handle incoming IMU punch classification messages.
        
        Converts valid punch detections to menu selections, respecting
        the confidence threshold and cooldown period.
        
        Args:
            msg: The IMU punch classification message.
        """
        # Skip if input is disabled
        if not self.enabled:
            return
        
        # Filter low-confidence detections
        if msg.confidence < self.confidence_threshold:
            return
        
        # Enforce cooldown to prevent rapid selections
        now = self.get_clock().now().nanoseconds / 1e9
        if now - self.last_selection_time < self.cooldown:
            return
        
        # Map punch type to selection number
        punch_type = msg.punch_type.lower()
        selection = self.PUNCH_TO_SELECTION.get(punch_type)
        
        if selection is not None:
            # Publish the selection
            sel_msg = Int32()
            sel_msg.data = selection
            self.selection_pub.publish(sel_msg)
            
            self.last_selection_time = now
            self.get_logger().info(f"IMU selection: {punch_type} -> {selection}")


def main(args=None) -> None:
    """Entry point for the IMU input selector node."""
    rclpy.init(args=args)
    node = ImuInputSelector()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
