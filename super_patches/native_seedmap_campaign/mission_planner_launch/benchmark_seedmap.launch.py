import os.path

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
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
    declare_integrated_filter_cmd = DeclareLaunchArgument(
        'use_integrated_filter', default_value='false',
        description='run SUPER with the in-process native sector filter'
    )
    declare_filter_arguments_cmd = DeclareLaunchArgument(
        'filter_arguments', default_value='',
        description='semicolon-delimited native sector filter arguments'
    )

    waypoint_data = LaunchConfiguration('waypoint_data')
    drone_config = LaunchConfiguration('drone_config')
    super_config = LaunchConfiguration('super_config')
    use_integrated_filter = LaunchConfiguration('use_integrated_filter')
    filter_arguments = LaunchConfiguration('filter_arguments')

    ld = LaunchDescription()
    ld.add_action(declare_waypoint_data_cmd)
    ld.add_action(declare_drone_config_cmd)
    ld.add_action(declare_super_config_cmd)
    ld.add_action(declare_integrated_filter_cmd)
    ld.add_action(declare_filter_arguments_cmd)

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
        condition=UnlessCondition(use_integrated_filter),
        parameters=[{
            'config_name': super_config,
        }]
    )
    ld.add_action(SUPER)

    SUPER_with_filter = Node(
        package='super_planner',
        executable='fsm_node_with_sector',
        output='screen',
        condition=IfCondition(use_integrated_filter),
        parameters=[{
            'config_name': super_config,
            'filter_arguments': filter_arguments,
        }]
    )
    ld.add_action(SUPER_with_filter)

    return ld
