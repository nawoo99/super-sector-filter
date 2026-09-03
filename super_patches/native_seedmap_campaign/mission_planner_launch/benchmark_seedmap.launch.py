import os.path

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PythonExpression

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
    declare_sensor_frontend_cmd = DeclareLaunchArgument(
        'use_sensor_frontend', default_value='false',
        description=('compose simulator and native filter, disable raw cloud '
                     'DDS, and emit only filtered cloud plus risk verdict')
    )
    declare_integrated_full_cmd = DeclareLaunchArgument(
        'use_integrated_full', default_value='false',
        description=('compose simulator and SUPER for direct latest-only '
                     'Full-cloud handoff without changing cloud contents')
    )

    waypoint_data = LaunchConfiguration('waypoint_data')
    drone_config = LaunchConfiguration('drone_config')
    super_config = LaunchConfiguration('super_config')
    use_integrated_filter = LaunchConfiguration('use_integrated_filter')
    filter_arguments = LaunchConfiguration('filter_arguments')
    use_sensor_frontend = LaunchConfiguration('use_sensor_frontend')
    use_integrated_full = LaunchConfiguration('use_integrated_full')
    external_simulator = PythonExpression([
        "'", use_sensor_frontend, "' != 'true' and '",
        use_integrated_full, "' != 'true'"
    ])
    external_super = PythonExpression([
        "'", use_integrated_filter, "' != 'true' and '",
        use_integrated_full, "' != 'true'"
    ])

    ld = LaunchDescription()
    ld.add_action(declare_waypoint_data_cmd)
    ld.add_action(declare_drone_config_cmd)
    ld.add_action(declare_super_config_cmd)
    ld.add_action(declare_integrated_filter_cmd)
    ld.add_action(declare_filter_arguments_cmd)
    ld.add_action(declare_sensor_frontend_cmd)
    ld.add_action(declare_integrated_full_cmd)

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
        condition=IfCondition(external_simulator),
        parameters=[{
            'config_name': drone_config,
        }]
    )
    ld.add_action(perfect_drone_sim)

    perfect_drone_frontend = Node(
        package='perfect_drone_sim',
        executable='perfect_drone_frontend_node',
        output='log',
        condition=IfCondition(use_sensor_frontend),
        parameters=[{
            'config_name': drone_config,
            'filter_arguments': filter_arguments,
        }]
    )
    ld.add_action(perfect_drone_frontend)

    perfect_drone_full = Node(
        package='perfect_drone_sim',
        executable='perfect_drone_full_node',
        output='screen',
        condition=IfCondition(use_integrated_full),
        parameters=[{
            'drone_config': drone_config,
            'super_config': super_config,
        }]
    )
    ld.add_action(perfect_drone_full)

    SUPER = Node(
        package='super_planner',
        executable='fsm_node',
        output='screen',
        condition=IfCondition(external_super),
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
