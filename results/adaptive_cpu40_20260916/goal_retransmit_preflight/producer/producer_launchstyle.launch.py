"""Matches benchmark mission output='log'; no simulator/FSM is launched."""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([Node(package='mission_planner', executable='waypoint_mission',
                                   name='waypoint_mission', output='log',
                                   parameters=[{'config_name': 'waypoint.yaml', 'data_name': 'loop24.txt'}])])
