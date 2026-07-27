import os.path

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


def generate_launch_description():
    declare_waypoint_data_cmd = DeclareLaunchArgument(
        'waypoint_data', default_value='loop9.txt',
        description='mission_planner data file (waypoints)'
    )
    declare_drone_config_cmd = DeclareLaunchArgument(
        'drone_config', default_value='seed1.yaml',
        description='perfect_drone_sim config file'
    )
    declare_super_config_cmd = DeclareLaunchArgument(
        'super_config', default_value='static_seedmaps.yaml',
        description='super_planner config file'
    )

    waypoint_data = LaunchConfiguration('waypoint_data')
    drone_config = LaunchConfiguration('drone_config')
    super_config = LaunchConfiguration('super_config')

    ld = LaunchDescription()
    ld.add_action(declare_waypoint_data_cmd)
    ld.add_action(declare_drone_config_cmd)
    ld.add_action(declare_super_config_cmd)

    mission_planner = Node(
        package='mission_planner',
        executable='waypoint_mission',
        output='log',
        parameters=[{
            'config_name': 'waypoint.yaml',
            'data_name': waypoint_data,
        }]
    )
    ld.add_action(mission_planner)

    perfect_drone_sim = Node(
        package='perfect_drone_sim',
        executable='perfect_drone_node',
        output='log',
        parameters=[{
            'config_name': drone_config,
        }]
    )
    ld.add_action(perfect_drone_sim)

    SUPER = Node(
        package='super_planner',
        executable='fsm_node',
        output='screen',
        parameters=[{
            'config_name': super_config,
        }]
    )
    ld.add_action(SUPER)

    return ld
