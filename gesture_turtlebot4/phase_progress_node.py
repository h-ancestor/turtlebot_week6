#!/usr/bin/env python3
"""Track phase 2 completion and signal when the required behaviors are demonstrated."""
import json
import os
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

REQUIRED_BEHAVIORS = {'forward_backward', 'circle'}


class PhaseProgressNode(Node):
    def __init__(self):
        super().__init__('phase_progress_node')
        self.declare_parameter('output_dir', '')
        self.output_dir = str(self.get_parameter('output_dir').value)
        if not self.output_dir:
            raise ValueError('output_dir is required')
        os.makedirs(self.output_dir, exist_ok=True)
        self.events_path = os.path.join(self.output_dir, 'behavior_events.jsonl')
        self.progress_path = os.path.join(self.output_dir, 'phase2_progress.txt')
        self.done_path = os.path.join(self.output_dir, 'phase2_complete.txt')
        self.completed = set()
        self.stop_demonstrated = False
        self.cancel_demonstrated = False
        self.finished = False
        self.sub = self.create_subscription(String, '/robot_behavior_status', self.on_status, 20)
        self.timer = self.create_timer(0.5, self.write_progress)
        self.write_progress()
        self.get_logger().info('Phase 2 monitor ready; complete forward/back and circle, active stop, and cancel.')

    def on_status(self, msg):
        try:
            event = json.loads(msg.data)
        except (ValueError, TypeError):
            self.get_logger().warning(f'Ignoring invalid behavior status: {msg.data}')
            return
        with open(self.events_path, 'a', encoding='utf-8') as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + '\n')
        kind = event.get('event')
        if kind == 'completed' and event.get('behavior') in REQUIRED_BEHAVIORS:
            self.completed.add(event['behavior'])
            self.get_logger().info(f"Behavior completed: {event['behavior']}")
        elif kind == 'stopped' and event.get('was_active'):
            self.stop_demonstrated = True
            self.get_logger().info('Active behavior stopped by Open Palm.')
        elif kind == 'cancelled' and event.get('had_target'):
            self.cancel_demonstrated = True
            self.get_logger().info('Selected or active behavior cancelled by Closed Fist.')
        self.write_progress()
        if (self.completed == REQUIRED_BEHAVIORS and self.stop_demonstrated
                and self.cancel_demonstrated and not self.finished):
            self.finished = True
            with open(self.done_path, 'w', encoding='utf-8') as stream:
                stream.write(time.strftime('%Y-%m-%dT%H:%M:%S%z') + '\n')
            self.get_logger().info('All configured phase 2 behaviors demonstrated; finishing recording.')

    def write_progress(self):
        behaviors = ', '.join(sorted(self.completed)) or 'none'
        remaining = sorted(REQUIRED_BEHAVIORS - self.completed)
        text = (
            f'Đã hoàn tất hành vi: {behaviors}\n'
            f'Còn lại: {", ".join(remaining) or "không còn"}\n'
            f'Xòe bàn tay dừng robot đang chạy: {"rồi" if self.stop_demonstrated else "chưa"}\n'
            f'Nắm bàn tay hủy hành vi: {"rồi" if self.cancel_demonstrated else "chưa"}\n'
        )
        temp_path = self.progress_path + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as stream:
            stream.write(text)
        os.replace(temp_path, self.progress_path)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = PhaseProgressNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
