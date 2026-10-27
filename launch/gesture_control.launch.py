from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, Shutdown
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    behavior = Node(
        package='gesture_turtlebot4', executable='robot_behavior_node',
        name='robot_behavior_node', output='screen', parameters=[{
            'cmd_vel_topic': LaunchConfiguration('cmd_vel_topic'),
        }])
    recognizer = Node(
        package='gesture_turtlebot4', executable='gesture_recognition_node',
        name='gesture_recognition_node', output='screen', parameters=[{
            'camera_index': LaunchConfiguration('camera_index'),
            'show_window': LaunchConfiguration('show_window'),
            'model_path': LaunchConfiguration('model_path'),
        }])
    return LaunchDescription([
        DeclareLaunchArgument('camera_index', default_value='0'),
        DeclareLaunchArgument('cmd_vel_topic', default_value='/cmd_vel'),
        DeclareLaunchArgument('show_window', default_value='true'),
        DeclareLaunchArgument('model_path', default_value=''),
        behavior,
        recognizer,
        RegisterEventHandler(OnProcessExit(
            target_action=behavior,
            on_exit=[Shutdown(reason='Robot behavior node exited')],
        )),
        RegisterEventHandler(OnProcessExit(
            target_action=recognizer,
            on_exit=[Shutdown(reason='Gesture recognition node exited')],
        )),
    ])
