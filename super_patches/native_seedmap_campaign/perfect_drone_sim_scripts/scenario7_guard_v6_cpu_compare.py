#!/usr/bin/env python3
"""Diagnostic v6 child: stop and refresh Full before following a new goal."""
from pathlib import Path
import re

import scenario7_guard_v5_cpu_compare as previous


V6_SOURCE = Path(__file__).resolve()
V6_INSTALL_ROOT = '/root/super_ws/scenario7_guard_v6_20260927/install'
V6_CHANGED = (
    'super_planner/include/fsm/fsm.h',
    'super_planner/src/super_core/fsm.cpp',
    'super_planner/include/ros_interface/ros2/fsm_ros2.hpp',
    'super_planner/test/goal_change_full_refresh_v6_source_contract_test.py',
)


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
         "                result['source_acquisition']['checks']['goal_change_full_refresh_v6'] = v6_valid\n"),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise ValueError('Guard-v6 child adaptation cardinality changed: ' + old)
        source = source.replace(old, new, 1)
    return source


def main():
    global original_adapt_v6
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
