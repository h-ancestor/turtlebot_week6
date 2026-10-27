#!/usr/bin/env python3
"""Safe, finite-duration gesture behaviors for TurtleBot 4."""
import json
import math
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import String


class RobotBehaviorNode(Node):
    def __init__(self):
        super().__init__('robot_behavior_node')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('gesture_topic', '/detected_gesture')
        self.declare_parameter('gesture_timeout_sec', 2.0)
        self.declare_parameter('event_cooldown_sec', 0.8)
        self.declare_parameter('linear_speed', 0.12)
        self.declare_parameter('angular_speed', 0.35)
        self.declare_parameter('square_duration_sec', 1.2)
        self.declare_parameter('circle_radius_m', 0.45)
        self.declare_parameter('circle_duration_sec', 18.0)
        self.pub = self.create_publisher(Twist, str(self.get_parameter('cmd_vel_topic').value), 10)
        self.status_pub = self.create_publisher(String, '/robot_behavior_status', 10)
        self.sub = self.create_subscription(String, str(self.get_parameter('gesture_topic').value), self.on_gesture, 10)
        self.timer = self.create_timer(0.05, self.control_tick)
        self.last_message = time.monotonic()
        self.last_event = 0.0
        self.last_gesture = 'NONE'
        self.armed = True
        self.selected = None
        self.active = None
        self.phase = 0
        self.phase_started = 0.0
        self.run_started = 0.0
        self.duration = 0.0
        self.linear = float(self.get_parameter('linear_speed').value)
        self.angular = float(self.get_parameter('angular_speed').value)
        self.get_logger().info('Waiting for gesture selection. Robot starts stopped.')
        self.stop()

    def on_gesture(self, msg):
        self.last_message = time.monotonic()
        try:
            data = json.loads(msg.data)
            gesture = str(data.get('gesture', 'NONE'))
            confidence = float(data.get('confidence', 0.0))
        except (ValueError, TypeError, AttributeError):
            # Accept a plain label as a convenience for ROS CLI/manual debugging.
            gesture, confidence = msg.data.strip(), 1.0
        if gesture == 'NONE':
            self.last_gesture = 'NONE'
            self.armed = True
            return
        if confidence < 0.55 or gesture == self.last_gesture:
            return
        self.last_gesture = gesture
        now = time.monotonic()
        if gesture == 'Open_Palm':
            was_active = self.active is not None
            had_target = was_active or self.selected is not None
            self.cancel('Emergency stop: Open Palm')
            self.publish_status('stopped', gesture=gesture, was_active=was_active, had_target=had_target)
            self.armed = False
            return
        if gesture == 'Closed_Fist':
            was_active = self.active is not None
            had_target = was_active or self.selected is not None
            self.cancel('Cancelled: Closed Fist')
            self.publish_status('cancelled', gesture=gesture, was_active=was_active, had_target=had_target)
            self.armed = False
            return
        if not self.armed or now - self.last_event < float(self.get_parameter('event_cooldown_sec').value):
            return
        self.armed = False
        self.last_event = now
        if gesture in ('Pointing_Up', 'Victory'):
            self.selected = {'Pointing_Up': 'forward_backward', 'Victory': 'circle'}[gesture]
            self.get_logger().info(f'Selected: {self.selected}. Show Thumbs Up to confirm.')
            self.publish_status('selected', behavior=self.selected, gesture=gesture)
        elif gesture == 'Thumb_Up':
            if self.selected is None:
                self.get_logger().warning('No behavior selected; show Pointing Up or Victory first.')
            else:
                self.start_behavior(self.selected)
                self.selected = None

    def start_behavior(self, name):
        now = time.monotonic()
        self.active = name
        self.run_started = now
        self.phase_started = now
        self.phase = 0
        if name == 'forward_backward':
            self.duration = 8.0 * float(self.get_parameter('square_duration_sec').value)
        elif name == 'circle':
            self.duration = float(self.get_parameter('circle_duration_sec').value)
        self.get_logger().info(f'Confirmed. Executing {name}.')
        self.publish_status('started', behavior=name)

    def control_tick(self):
        now = time.monotonic()
        if now - self.last_message > float(self.get_parameter('gesture_timeout_sec').value):
            if self.active is not None:
                self.get_logger().warning('Gesture control heartbeat lost; stopping behavior.')
            self.cancel('Control heartbeat timeout')
            return
        if self.active is None:
            self.stop()
            return
        elapsed = now - self.run_started
        if elapsed >= self.duration:
            finished = self.active
            self.active = None
            self.stop()
            self.get_logger().info(f'Completed: {finished}.')
            self.publish_status('completed', behavior=finished)
            return
        cmd = Twist()
        if self.active == 'forward_backward':
            leg = float(self.get_parameter('square_duration_sec').value)
            cmd.linear.x = self.linear if int(elapsed / leg) % 2 == 0 else -self.linear
        elif self.active == 'circle':
            radius = max(0.1, float(self.get_parameter('circle_radius_m').value))
            cmd.linear.x = self.linear
            cmd.angular.z = min(self.angular, self.linear / radius)
        self.pub.publish(cmd)

    def cancel(self, reason):
        if self.active or self.selected:
            self.get_logger().warning(reason)
        self.active = None
        self.selected = None
        self.stop()

    def stop(self):
        self.pub.publish(Twist())

    def publish_status(self, event, **fields):
        payload = {'event': event, 'stamp': time.time(), **fields}
        msg = String()
        msg.data = json.dumps(payload, separators=(',', ':'))
        self.status_pub.publish(msg)

    def destroy_node(self):
        self.stop()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = RobotBehaviorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cancel('Node shutting down')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
