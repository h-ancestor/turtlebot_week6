from setuptools import setup
from glob import glob
import os

package_name = 'gesture_turtlebot4'
setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'models'), glob('models/*.task')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Student',
    maintainer_email='student@example.com',
    description='Gesture recognition and safe TurtleBot 4 behavior control',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'gesture_recognition_node = gesture_turtlebot4.gesture_recognition_node:main',
        'robot_behavior_node = gesture_turtlebot4.robot_behavior_node:main',
        'phase_progress_node = gesture_turtlebot4.phase_progress_node:main',
    ]},
)
