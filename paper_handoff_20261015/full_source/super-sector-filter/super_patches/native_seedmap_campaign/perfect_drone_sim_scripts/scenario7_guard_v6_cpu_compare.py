#!/usr/bin/env python3
"""Canonical scenario7 child with Active-Yaw as the default Sector mode.

The historical filename is retained because the campaign entrypoints already
import it.  ``mode=sector`` now always enables the certified Active-Yaw
acquisition and the zero-return scan heartbeat; callers that need the legacy
body-forward-only ablation must use a separately named legacy wrapper.
"""
from pathlib import Path
import re

import scenario7_guard_v5_cpu_compare as previous


V6_SOURCE = Path(__file__).resolve()
V6_INSTALL_ROOT = '/root/super_ws/sector_active_yaw_scan_v1_20260929/install'
V6_CHANGED = (
    'rog_map/include/rog_map/rog_map.h',
    'rog_map/include/rog_map_ros/rog_map_ros2.hpp',
    'rog_map/src/rog_map/rog_map.cpp',
    'super_planner/CMakeLists.txt',
    'super_planner/include/fsm/fsm.h',
    'super_planner/include/fsm/active_yaw_scan_policy.hpp',
    'super_planner/src/super_core/fsm.cpp',
    'super_planner/include/ros_interface/ros2/fsm_ros2.hpp',
    'super_planner/test/active_yaw_scan_policy_test.cpp',
    'super_planner/test/goal_change_full_refresh_v6_source_contract_test.py',
)


def verify_default_sector_contract():
    """Fail before a campaign starts if the canonical Sector runtime is wrong."""
    install = Path(V6_INSTALL_ROOT)
    fsm_binary = install / 'super_planner/lib/super_planner/fsm_node'
    rog_header = install / 'rog_map/include/rog_map_ros/rog_map_ros2.hpp'
    failures = []
    if not fsm_binary.is_file():
        failures.append(f'missing Active-Yaw FSM binary: {fsm_binary}')
    else:
        binary = fsm_binary.read_bytes()
        for marker in (
                b'SUPER_SECTOR_ACTIVE_YAW_SCAN',
                b'[ACTIVE_YAW_SCAN_ARM]',
                b'[ACTIVE_YAW_SCAN_MAP_READY]',
                b'SUPER_SECTOR_EMPTY_SCAN_HEARTBEAT'):
            if marker not in binary:
                failures.append(
                    f'Active-Yaw FSM binary lacks marker {marker!r}')
    if not rog_header.is_file():
        failures.append(f'missing Active-Yaw ROG-Map header: {rog_header}')
    elif 'SUPER_SECTOR_EMPTY_SCAN_HEARTBEAT' not in rog_header.read_text(
            errors='replace'):
        failures.append('installed ROG-Map lacks empty-scan heartbeat contract')
    if failures:
        raise RuntimeError('Default Sector preflight failed: ' + '; '.join(failures))
    return {
        'valid': True,
        'install_root': str(install),
        'sector_mode': 'active_yaw',
        'active_yaw_scan': True,
        'empty_scan_heartbeat': True,
    }


def adapt_v6(source):
    source = original_adapt_v6(source)
    replacements = (
        ("    files.update((V2_CHILD_SOURCE, V3_CHILD_SOURCE, V4_SOURCE, V5_SOURCE))",
         "    files.update((V2_CHILD_SOURCE, V3_CHILD_SOURCE, V4_SOURCE, V5_SOURCE))\n"
         "    files.add(Path('/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts/scenario7_guard_v6_cpu_compare.py'))\n"
         "    files.update(SOURCE / path for path in (\n"
         "        'super_planner/include/fsm/fsm.h',\n"
         "        'super_planner/src/super_core/fsm.cpp',\n"
         "        'super_planner/include/ros_interface/ros2/fsm_ros2.hpp',\n"
         "        'super_planner/test/goal_change_full_refresh_v6_source_contract_test.py'))"),
        ("            for mode in args.modes:\n"
         "                os.environ['SUPER_FRONTEND_DEDICATED_EXECUTOR'] =",
         "            for mode in args.modes:\n"
         "                os.environ['SUPER_GOAL_CHANGE_FULL_REFRESH_V6'] = (\n"
         "                    '1' if mode == 'adaptive' else '0')\n"
         "                os.environ['SUPER_SECTOR_ACTIVE_YAW_SCAN'] = (\n"
         "                    '1' if mode == 'sector' else '0')\n"
         "                os.environ['SUPER_SECTOR_EMPTY_SCAN_HEARTBEAT'] = (\n"
         "                    '1' if mode == 'sector' else '0')\n"
         "                os.environ['SUPER_FRONTEND_DEDICATED_EXECUTOR'] ="),
        ("                result['source_acquisition']['checks']['stopped_hold_v5'] = v5_valid\n",
         "                result['source_acquisition']['checks']['stopped_hold_v5'] = v5_valid\n"
         "                v6_rows = re.findall(r'\\[GOAL_CHANGE_FULL_REFRESH_V6\\][^\\r\\n]*', stack)\n"
         "                v6_expected = 'true' if mode == 'adaptive' else 'false'\n"
         "                v6_valid = len(v6_rows) == 1 and all(token in v6_rows[0] for token in (\n"
         "                    'enabled=' + v6_expected, 'distinct_identity_only=true',\n"
         "                    'following_only=true', 'stop_before_full_ack=true',\n"
         "                    'certified_release=true', 'default_off=true'))\n"
         "                result['goal_change_full_refresh_v6_audit'] = dict(\n"
         "                    valid=v6_valid, expected_enabled=v6_expected, records=v6_rows)\n"
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
         "                result['source_acquisition']['checks']['active_yaw_scan_default'] = yaw_valid\n"),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise ValueError('Guard-v6 child adaptation cardinality changed: ' + old)
        source = source.replace(old, new, 1)
    return source


def main():
    global original_adapt_v6
    verify_default_sector_contract()
    original_adapt_v6 = previous.adapt_v5
    old_install = previous.V5_INSTALL_ROOT
    previous.adapt_v5 = adapt_v6
    previous.V5_INSTALL_ROOT = V6_INSTALL_ROOT
    try:
        return previous.main()
    finally:
        previous.V5_INSTALL_ROOT = old_install
        previous.adapt_v5 = original_adapt_v6


if __name__ == '__main__':
    raise SystemExit(main())
