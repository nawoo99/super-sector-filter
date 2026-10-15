"""Explicit reader-only RViz profile selection; legacy remains the default.

For a late/reconnecting viewer of the one-shot map, launch with durable:=true.
The simulator must independently use SUPER_STATIC_PC_DURABLE=1 and
SUPER_STATIC_PC_LATCHED_ONCE=1. This launch sets no publisher environment and
starts no simulator, planner, mission or goal publisher.
"""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


VIEWS = ('watch_sector', 'top_down', 'fpv', 'benchmark')


def select_rviz_filename(view, durable):
    if view not in VIEWS:
        raise ValueError('view must be one of: ' + ', '.join(VIEWS))
    if durable not in ('false', 'true'):
        raise ValueError('durable must be exactly false or true')
    return view + ('_durable' if durable == 'true' else '') + '.rviz'


def launch_view(context):
    view = LaunchConfiguration('view').perform(context)
    durable = LaunchConfiguration('durable').perform(context)
    filename = select_rviz_filename(view, durable)
    config = Path(get_package_share_directory('perfect_drone_sim')) / 'rviz2' / filename
    if not config.is_file():
        raise RuntimeError('RViz config is not installed: ' + str(config))
    return [
        LogInfo(msg='[STATIC_MAP_VIEW] durable=' + durable + ' config=' + str(config)
                + ' reader_only=1 publisher_settings_unchanged=1'),
        Node(package='rviz2', executable='rviz2', arguments=['-d', str(config)],
             output='screen'),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('view', default_value='watch_sector', choices=VIEWS,
                              description='Existing camera/display layout to load'),
        DeclareLaunchArgument('durable', default_value='false', choices=('false', 'true'),
                              description='Request reliable/transient-local static map; '
                                          'requires matching opted-in publisher'),
        OpaqueFunction(function=launch_view),
    ])
