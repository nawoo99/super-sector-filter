#!/usr/bin/env python3
"""Default-off Fixed Sector + certified active-yaw acquisition child."""
from pathlib import Path
import re

import scenario7_guard_v6_cpu_compare as previous


V1_SOURCE = Path(__file__).resolve()
V1_INSTALL_ROOT = '/root/super_ws/sector_active_yaw_scan_v1_20260929/install'
V1_CHANGED = (
    'rog_map/include/rog_map/rog_map.h',
    'rog_map/include/rog_map_ros/rog_map_ros2.hpp',
    'rog_map/src/rog_map/rog_map.cpp',
    'super_planner/CMakeLists.txt',
    'super_planner/include/fsm/active_yaw_scan_policy.hpp',
    'super_planner/include/ros_interface/ros2/fsm_ros2.hpp',
    'super_planner/test/active_yaw_scan_policy_test.cpp',
)


def adapt_v1(source):
    source = original_adapt_v1(source)
    replacements = (
        ("                os.environ['SUPER_GOAL_CHANGE_FULL_REFRESH_V6'] = (\n"
         "                    '1' if mode == 'adaptive' else '0')\n"
         "                os.environ['SUPER_FRONTEND_DEDICATED_EXECUTOR'] =",
         "                os.environ['SUPER_GOAL_CHANGE_FULL_REFRESH_V6'] = (\n"
         "                    '1' if mode == 'adaptive' else '0')\n"
         "                os.environ['SUPER_SECTOR_ACTIVE_YAW_SCAN'] = (\n"
         "                    '1' if mode == 'sector' else '0')\n"
         "                os.environ['SUPER_SECTOR_EMPTY_SCAN_HEARTBEAT'] = (\n"
         "                    '1' if mode == 'sector' else '0')\n"
         "                os.environ['SUPER_FRONTEND_DEDICATED_EXECUTOR'] ="),
        ("    files.add(Path('/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts/scenario7_guard_v6_cpu_compare.py'))\n",
         "    files.add(Path('/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts/scenario7_guard_v6_cpu_compare.py'))\n"
         "    files.add(Path('/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts/scenario7_active_yaw_scan_v1_cpu_compare.py'))\n"
         "    files.update(SOURCE / path for path in (\n"
         "        'rog_map/include/rog_map/rog_map.h',\n"
         "        'rog_map/include/rog_map_ros/rog_map_ros2.hpp',\n"
         "        'rog_map/src/rog_map/rog_map.cpp',\n"
         "        'super_planner/CMakeLists.txt',\n"
         "        'super_planner/include/fsm/active_yaw_scan_policy.hpp',\n"
         "        'super_planner/include/ros_interface/ros2/fsm_ros2.hpp',\n"
         "        'super_planner/test/active_yaw_scan_policy_test.cpp'))\n"),
        ("                result['source_acquisition']['checks']['goal_change_full_refresh_v6'] = v6_valid\n",
         "                result['source_acquisition']['checks']['goal_change_full_refresh_v6'] = v6_valid\n"
         "                yaw_rows = re.findall(r'\\[ACTIVE_YAW_SCAN\\][^\\r\\n]*', stack)\n"
         "                yaw_expected = 'true' if mode == 'sector' else 'false'\n"
         "                yaw_valid = len(yaw_rows) == 1 and all(token in yaw_rows[0] for token in (\n"
         "                    'enabled=' + yaw_expected, 'mode=fixed_sector',\n"
         "                    'sequence=stop_yaw_fresh_map_replan', 'default_off=true'))\n"
         "                result['active_yaw_scan_v1_audit'] = dict(\n"
         "                    valid=yaw_valid, expected_enabled=yaw_expected, records=yaw_rows,\n"
         "                    arms=len(re.findall(r'\\[ACTIVE_YAW_SCAN_ARM\\]', stack)),\n"
         "                    map_ready=len(re.findall(r'\\[ACTIVE_YAW_SCAN_MAP_READY\\]', stack)),\n"
         "                    exhausted=len(re.findall(r'\\[ACTIVE_YAW_SCAN_EXHAUSTED\\]', stack)))\n"
         "                result['source_acquisition']['checks']['active_yaw_scan_v1'] = yaw_valid\n"),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise ValueError('Active-yaw child adaptation cardinality changed: ' + old)
        source = source.replace(old, new, 1)
    return source


def main():
    global original_adapt_v1
    original_adapt_v1 = previous.adapt_v6
    old_install = previous.V6_INSTALL_ROOT
    previous.adapt_v6 = adapt_v1
    previous.V6_INSTALL_ROOT = V1_INSTALL_ROOT
    try:
        return previous.main()
    finally:
        previous.V6_INSTALL_ROOT = old_install
        previous.adapt_v6 = original_adapt_v1


if __name__ == '__main__':
    raise SystemExit(main())
