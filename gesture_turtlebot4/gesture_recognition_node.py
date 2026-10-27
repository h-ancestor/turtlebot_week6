#!/usr/bin/env python3
"""Laptop webcam gesture recognizer. Opens a camera only after node startup."""
import json
import os
import time
from collections import deque

from PIL import Image, ImageDraw, ImageFont
import cv2
import mediapipe as mp
import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from std_msgs.msg import String

MODEL_URL = ('https://storage.googleapis.com/mediapipe-models/gesture_recognizer/'
             'gesture_recognizer/float16/1/gesture_recognizer.task')
RECOGNIZED_GESTURES = {'Waving', 'Pointing_Up', 'Victory', 'Thumb_Up', 'Open_Palm', 'Closed_Fist'}
GESTURE_NAMES_VI = {
    'NONE': 'Chưa nhận rõ',
    'Waving': 'Vẫy tay',
    'Pointing_Up': 'Giơ một ngón tay',
    'Victory': 'Giơ hai ngón hình chữ V',
    'Thumb_Up': 'Giơ ngón cái',
    'Open_Palm': 'Xòe bàn tay',
    'Closed_Fist': 'Nắm bàn tay',
}


class GestureRecognitionNode(Node):
    def __init__(self):
        super().__init__('gesture_recognition_node')
        self.declare_parameter('camera_index', 0)
        self.declare_parameter('model_path', '')
        self.declare_parameter('confidence_threshold', 0.65)
        self.declare_parameter('stable_frames', 4)
        self.declare_parameter('camera_fps', 15.0)
        self.declare_parameter('show_window', True)
        self.declare_parameter('publish_rate_hz', 10.0)
        self.declare_parameter('unique_gestures_to_finish', 0)
        self.declare_parameter('recognition_start_delay_sec', 0.0)
        self.declare_parameter('progress_file', '')
        self.publisher = self.create_publisher(String, '/detected_gesture', 10)
        self.threshold = float(self.get_parameter('confidence_threshold').value)
        self.stable_frames = max(1, int(self.get_parameter('stable_frames').value))
        self.show_window = bool(self.get_parameter('show_window').value)
        font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        self.font_large = ImageFont.truetype(font_path, 21) if os.path.exists(font_path) else ImageFont.load_default()
        self.font_small = ImageFont.truetype(font_path, 16) if os.path.exists(font_path) else ImageFont.load_default()
        self.unique_target = max(0, int(self.get_parameter('unique_gestures_to_finish').value))
        self.start_recognition_at = time.monotonic() + max(0.0, float(
            self.get_parameter('recognition_start_delay_sec').value))
        self.progress_file = str(self.get_parameter('progress_file').value)
        self.unique_gestures = set()
        model_path = str(self.get_parameter('model_path').value)
        if not model_path:
            model_path = os.path.join(get_package_share_directory('gesture_turtlebot4'),
                                      'models', 'gesture_recognizer.task')
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f'Model missing: {model_path}. Run ./setup_environment.sh')
        base = mp.tasks.BaseOptions(model_asset_path=model_path)
        options = mp.tasks.vision.GestureRecognizerOptions(
            base_options=base, running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_hands=1, min_hand_detection_confidence=0.55,
            min_hand_presence_confidence=0.55, min_tracking_confidence=0.55)
        self.recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(options)
        # Webcam is intentionally opened only when this executable is launched.
        self.camera = cv2.VideoCapture(int(self.get_parameter('camera_index').value))
        if not self.camera.isOpened():
            self.recognizer.close()
            raise RuntimeError('Cannot open webcam. Check camera permission and camera_index.')
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.history = deque(maxlen=self.stable_frames)
        self.wrist_x = deque(maxlen=20)
        self.current = ('NONE', 0.0)
        self.last_publish = 0.0
        self.timer = self.create_timer(1.0 / max(1.0, float(self.get_parameter('camera_fps').value)), self.process_frame)
        self.get_logger().info('Webcam gesture recognition running; press q in its window to quit.')

    def process_frame(self):
        ok, frame = self.camera.read()
        if not ok:
            self.get_logger().warning('Webcam frame unavailable; publishing NONE')
            self.publish('NONE', 0.0)
            return
        frame = cv2.flip(frame, 1)
        if time.monotonic() < self.start_recognition_at:
            remaining = max(0, int(self.start_recognition_at - time.monotonic() + 0.99))
            self.publish('NONE', 0.0)
            if self.show_window:
                frame = self.draw_overlay(frame, [
                    f'Chuẩn bị nhận diện cử chỉ: {remaining} giây',
                    'Hãy đưa bàn tay vào giữa khung hình.',
                ])
                cv2.imshow('TurtleBot 4 - Dieu khien bang cu chi tay', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    rclpy.shutdown()
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.recognizer.recognize(image)
        gesture, score = 'NONE', 0.0
        if result.gestures and result.gestures[0]:
            category = result.gestures[0][0]
            gesture, score = category.category_name, float(category.score)
            if result.hand_landmarks:
                self.wrist_x.append(float(result.hand_landmarks[0][0].x))
            if gesture == 'Open_Palm' and self.is_waving():
                gesture = 'Waving'
        else:
            self.wrist_x.clear()
        if score < self.threshold:
            gesture, score = 'NONE', 0.0
        self.history.append(gesture)
        stable = gesture if len(self.history) == self.stable_frames and all(x == gesture for x in self.history) else 'NONE'
        stable_score = score if stable != 'NONE' else 0.0
        self.current = (stable, stable_score)
        self.publish(stable, stable_score)
        phase_complete = self.record_unique_gesture(stable, stable_score)
        if self.show_window:
            shown_name = GESTURE_NAMES_VI.get(stable, stable)
            if self.unique_target:
                seen = ', '.join(GESTURE_NAMES_VI.get(g, g) for g in sorted(self.unique_gestures)) or 'chua co'
                lines = [
                    f'Nhận diện: {shown_name}  |  Độ tin cậy: {stable_score:.2f}',
                    f'Phần 1: đã nhận {len(self.unique_gestures)}/{self.unique_target} cử chỉ khác nhau',
                    f'Da nhan: {seen}',
                    'Làm cử chỉ mới rõ ràng; đủ 5 loại sẽ tự chuyển phần.',
                ]
            else:
                lines = [
                    f'Nhận diện: {shown_name}  |  Độ tin cậy: {stable_score:.2f}',
                    '1. Giơ 1 ngón -> ngón cái: tiến/lùi 4 chu kỳ',
                    '2. Giơ chữ V -> ngón cái: đi vòng',
                    '3. Chọn chữ V + ngón cái; đang quay: xòe tay dừng',
                    '4. Giơ 1 ngón rồi nắm tay để hủy lựa chọn',
                    'Rút tay khỏi hình giữa lúc chọn và xác nhận.',
                ]
            frame = self.draw_overlay(frame, lines)
            cv2.imshow('TurtleBot 4 - Dieu khien bang cu chi tay', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.get_logger().info('q pressed; shutting down safely.')
                rclpy.shutdown()
        if phase_complete and not getattr(self, 'phase_complete_logged', False):
            self.phase_complete_logged = True
            self.get_logger().info(f'Hoan tat nhan dien: da ghi nhan {len(self.unique_gestures)} cu chi khac nhau.')

    def draw_overlay(self, frame, lines):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        canvas = Image.fromarray(rgb)
        draw = ImageDraw.Draw(canvas, 'RGBA')
        line_height = 30 if self.unique_target else 27
        panel_height = 14 + line_height * len(lines)
        draw.rounded_rectangle((8, 8, 632, panel_height), radius=8, fill=(0, 0, 0, 185))
        for index, line in enumerate(lines):
            font = self.font_large if index == 0 else self.font_small
            draw.text((16, 12 + index * line_height), line, font=font, fill=(255, 255, 255, 255))
        import numpy as np
        return cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR)

    def record_unique_gesture(self, gesture, confidence):
        if not self.unique_target or gesture not in RECOGNIZED_GESTURES or gesture in self.unique_gestures:
            return False
        self.unique_gestures.add(gesture)
        record = {'gesture': gesture, 'confidence': round(float(confidence), 4),
                  'stamp': time.time(), 'unique_count': len(self.unique_gestures)}
        if self.progress_file:
            parent = os.path.dirname(os.path.abspath(self.progress_file))
            os.makedirs(parent, exist_ok=True)
            with open(self.progress_file, 'a', encoding='utf-8') as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + '\n')
        self.get_logger().info(
            f'Unique gesture {len(self.unique_gestures)}/{self.unique_target}: {gesture} ({confidence:.2f})')
        return len(self.unique_gestures) >= self.unique_target

    def is_waving(self):
        if len(self.wrist_x) < 10:
            return False
        values = list(self.wrist_x)
        if max(values) - min(values) < 0.12:
            return False
        directions = [1 if values[i] > values[i - 1] + 0.015 else
                      -1 if values[i] < values[i - 1] - 0.015 else 0
                      for i in range(1, len(values))]
        reversals = sum(1 for a, b in zip(directions, directions[1:]) if a * b == -1)
        return reversals >= 2

    def publish(self, gesture, confidence):
        msg = String()
        msg.data = json.dumps({'gesture': gesture, 'confidence': round(float(confidence), 4),
                               'stamp': time.time()}, separators=(',', ':'))
        self.publisher.publish(msg)

    def destroy_node(self):
        if hasattr(self, 'camera'):
            self.camera.release()
        if getattr(self, 'show_window', False):
            cv2.destroyAllWindows()
        if hasattr(self, 'recognizer'):
            self.recognizer.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = GestureRecognitionNode()
        rclpy.spin(node)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f'gesture_recognition_node: {exc}')
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
