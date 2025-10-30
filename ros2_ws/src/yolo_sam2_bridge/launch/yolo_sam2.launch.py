from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument

def generate_launch_description():
    params_file = LaunchConfiguration('params')
    return LaunchDescription([
        DeclareLaunchArgument('params', default_value='params.yaml'),
        Node(
            package='yolo_sam2_bridge',
            executable='yolo_sam2_node',
            name='yolo_sam2_node',
            output='screen',
            parameters=[params_file]
        )
    ])
