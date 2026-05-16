from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Offboard Fighter
        Node(
            package='nisankiran_core',
            executable='offboard_fighter',
            name='offboard_fighter_node',
            output='screen',
            emulate_tty=True
        ),

        # Radar Node WSO
        Node(
            package='nisankiran_telemetry',
            executable='radar',
            name='wso_radar_node',
            output='screen',
            emulate_tty=True
        ),

        # Vision Node 
        Node(
            package='nisankiran_telemetry',
            executable='vision',
            name='vision_tracker_node',
            output='screen',
            emulate_tty=True
        )
    ])