from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, Shutdown
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    recognizer = Node(
        package='gesture_turtlebot4', executable='gesture_recognition_node',
        name='gesture_recognition_node', output='screen', parameters=[{
            'camera_index': LaunchConfiguration('camera_index'),
            'show_window': LaunchConfiguration('show_window'),
            'model_path': LaunchConfiguration('model_path'),
            'unique_gestures_to_finish': LaunchConfiguration('unique_gestures_to_finish'),
            'recognition_start_delay_sec': LaunchConfiguration('recognition_start_delay_sec'),
            'progress_file': LaunchConfiguration('progress_file'),
        }])
    return LaunchDescription([
        DeclareLaunchArgument('camera_index', default_value='0'),
        DeclareLaunchArgument('show_window', default_value='true'),
        DeclareLaunchArgument('model_path', default_value=''),
        DeclareLaunchArgument('unique_gestures_to_finish', default_value='5'),
        DeclareLaunchArgument('recognition_start_delay_sec', default_value='0.0'),
        DeclareLaunchArgument('progress_file', default_value=''),
        recognizer,
        RegisterEventHandler(OnProcessExit(
            target_action=recognizer,
            on_exit=[Shutdown(reason='Recognition phase completed or recognizer exited')],
        )),
    ])
