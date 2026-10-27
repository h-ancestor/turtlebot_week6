# Bài thực hành 06 – Nhận diện cử chỉ tay và điều khiển TurtleBot 4

ROS 2 Humble package dùng OpenCV và MediaPipe để nhận diện cử chỉ từ webcam, sau đó gửi lệnh vận tốc cho TurtleBot 4 trong Gazebo.

## Thành phần

- `gesture_recognition_node`: đọc webcam, nhận diện cử chỉ, hiển thị nhãn/độ tin cậy và publish `/detected_gesture`.
- `robot_behavior_node`: subscribe cử chỉ, yêu cầu chọn rồi xác nhận hành vi, publish `/cmd_vel`; có lệnh dừng/hủy và watchdog mất tín hiệu.
- `phase_progress_node`: tùy chọn, lưu sự kiện hành vi và theo dõi tiến độ phần 2.
- `launch/`: launch nhận diện riêng hoặc nhận diện cùng node điều khiển.
- `models/gesture_recognizer.task`: model MediaPipe dùng khi chạy.

## Yêu cầu

Ubuntu 22.04, ROS 2 Humble, TurtleBot 4 Simulation từ bài trước, webcam, Python 3.10, OpenCV và MediaPipe. Hệ thống mô phỏng tuần trước cần nằm tại `"$HOME/Tương tác người - robot/bài thực hành 04"`; nếu khác, thay đường dẫn tương ứng trong các lệnh bên dưới.

## Cài đặt và build

Thay `<PUBLIC_REPOSITORY_URL>` bằng URL repository của bạn:

```bash
LAB_ROOT="$HOME/Tương tác người - robot"
PKG="$LAB_ROOT/thực _ hành _06/gesture_turtlebot4"
mkdir -p "$LAB_ROOT/thực _ hành _06"
git clone <PUBLIC_REPOSITORY_URL> "$PKG"
cd "$PKG"
./setup_environment.sh
source /opt/ros/humble/setup.bash
colcon --log-base log build --base-paths . --build-base build --install-base install --symlink-install
```

`setup_environment.sh` cài OpenCV/Pillow, cài các thư viện Python đã ghim phiên bản và tải model nếu model chưa có. Script dùng `sudo` cho các gói Ubuntu. Việc cài đặt/build không mở webcam; quyền camera chỉ cần khi chạy node nhận diện.

Trước khi public repository, sửa tên/email maintainer mẫu trong `setup.py` và `package.xml`, cùng dòng bản quyền mẫu trong `LICENSE`.

## Chạy thủ công

Các lệnh dưới đây không dùng bàn phím để điều khiển robot. `Ctrl+C` chỉ kết thúc tiến trình; nhấn `q` trong cửa sổ webcam chỉ đóng node nhận diện.

### Phần 1 – Nhận diện 5 cử chỉ

Mở terminal, nạp ROS và package, rồi chạy nhận diện độc lập:

```bash
LAB_ROOT="$HOME/Tương tác người - robot"
PKG="$LAB_ROOT/thực _ hành _06/gesture_turtlebot4"
source /opt/ros/humble/setup.bash
source "$PKG/install/setup.bash"
ros2 launch gesture_turtlebot4 gesture_recognition_only.launch.py \
  camera_index:=0 show_window:=true unique_gestures_to_finish:=5
```

Thực hiện 5 cử chỉ tĩnh khác nhau: xòe bàn tay (Open Palm), giơ một ngón (Pointing Up), giơ ngón cái (Thumb Up), nắm tay (Closed Fist), và chữ V (Victory). Khi nhận đủ 5 nhãn khác nhau, node tự đóng. Nếu webcam của bạn không ở camera index 0, thử `camera_index:=1`.

### Phần 2 – Điều khiển TurtleBot 4

**Terminal 1:** khởi chạy mô phỏng của bài trước:

```bash
LAB_ROOT="$HOME/Tương tác người - robot"
source /opt/ros/humble/setup.bash
source "$LAB_ROOT/bài thực hành 04/install/setup.bash"
ros2 launch turtlebot4_lab simulation.launch.py world:=warehouse model:=lite rviz:=true
```

**Terminal 2:** nạp các workspace và chạy node nhận diện cùng điều khiển:

```bash
LAB_ROOT="$HOME/Tương tác người - robot"
PKG="$LAB_ROOT/thực _ hành _06/gesture_turtlebot4"
source /opt/ros/humble/setup.bash
source "$LAB_ROOT/bài thực hành 04/install/setup.bash"
source "$PKG/install/setup.bash"
ros2 launch gesture_turtlebot4 gesture_control.launch.py \
  camera_index:=0 cmd_vel_topic:=/cmd_vel show_window:=true
```

Làm theo chỉ dẫn hiện trên cửa sổ webcam. Giơ một ngón để chọn tiến–lùi 4 chu kỳ, rồi rút tay khỏi khung hình và giơ ngón cái để xác nhận. Giơ chữ V để chọn quỹ đạo tròn, rồi giơ ngón cái để xác nhận. Khi robot đang chạy, xòe bàn tay để dừng; chọn hành vi rồi nắm tay trước khi xác nhận để hủy lựa chọn. Giữa cử chỉ chọn và xác nhận, đưa tay khỏi khung hình trong chốc lát để bộ lọc nhận trạng thái mới.

Cử chỉ vẫy tay không được bật trong phần điều khiển vì không nhận diện ổn định trong lượt demo đã ghi; mục Wave của đề gốc do đó chưa hoàn thành. Dùng vùng mô phỏng trống và quan sát robot trong suốt khi chạy. Nếu mất heartbeat cử chỉ, node điều khiển dừng hành vi sau 2 giây.

Kết thúc bằng `Ctrl+C` ở terminal điều khiển trước, sau đó mới dừng mô phỏng. Node điều khiển gửi vận tốc 0 khi dừng/hủy và khi kết thúc.

## Topic ROS 2

| Topic | Kiểu | Luồng |
|---|---|---|
| `/detected_gesture` | `std_msgs/msg/String` | Node nhận diện → node hành vi |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Node hành vi → TurtleBot 4 |
| `/robot_behavior_status` | `std_msgs/msg/String` | Node hành vi → theo dõi sự kiện |

Node nhận diện gửi nội dung JSON trong `String`, gồm nhãn cử chỉ, confidence và timestamp. Có thể ghi rosbag thủ công bằng `ros2 bag record` nếu cần lưu dữ liệu ROS. Repository này không chứa script tự động quay màn hình; video demo cần được ghi bằng công cụ ghi hình bạn chọn.

## Mức độ đáp ứng đề bài

Phần nhận diện ghi nhận 5 cử chỉ tĩnh. Phần điều khiển đã chạy tiến–lùi, đường tròn, dừng bằng lòng bàn tay mở và hủy bằng nắm tay. Cử chỉ Wave chưa được chứng minh ổn định và không được ánh xạ sang hành vi robot trong demo.
