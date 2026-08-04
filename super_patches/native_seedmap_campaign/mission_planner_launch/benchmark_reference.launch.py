import os.path

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_config_path = 'waypoint.yaml'
    default_data_path = 'benchmark.txt'
    perfect_drone_sim_config_name = 'dense.yaml'
    super_config_name = LaunchConfiguration('super_config')

    ld = LaunchDescription()
    ld.add_action(DeclareLaunchArgument(
        'super_config', default_value='static_reference.yaml',
        description='SUPER planner config file'))

    mission_planner = Node(
        package='mission_planner',
        executable='waypoint_mission',
        output='log',
        parameters=[{
            'config_name': default_config_path,
            'data_name': default_data_path
        }]
    )
    ld.add_action(mission_planner)

    perfect_drone_sim = Node(
        package='perfect_drone_sim',
        executable='perfect_drone_node',
        output='log',
        parameters=[{
            'config_name': perfect_drone_sim_config_name,
        }]
    )
    ld.add_action(perfect_drone_sim)

    SUPER = Node(
        package='super_planner',
        executable='fsm_node',
        output='screen',
        parameters=[{
            'config_name': super_config_name,
        }]
    )
    ld.add_action(SUPER)

    return ld
