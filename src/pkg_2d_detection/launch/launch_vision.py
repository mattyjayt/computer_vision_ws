from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    node = Node(
        package='pkg_2d_detection',
        executable='node_2d_detection',
        name='detection_node_2d'
    )

    return LaunchDescription([
        node
    ])