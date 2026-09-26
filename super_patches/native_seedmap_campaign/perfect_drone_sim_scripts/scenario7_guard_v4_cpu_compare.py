#!/usr/bin/env python3
"""Diagnostic v4 child: v3 gates plus the shared stopped-release contract."""
from pathlib import Path
import re

import scenario7_guard_v3_cpu_compare as previous


V4_SOURCE = Path(__file__).resolve()
V4_CHANGED = (
    'super_planner/CMakeLists.txt',
    'super_planner/include/data_structure/cmd_traj.h',
    'super_planner/include/data_structure/exp_traj.h',
    'super_planner/include/super_core/super_planner.h',
    'super_planner/src/super_core/super_planner.cpp',
    'super_planner/include/ros_interface/ros2/fsm_ros2.hpp',
    'super_planner/test/stopped_departure_clock_test.cpp',
    'super_planner/test/stopped_departure_v4_source_contract_test.py',
)


def adapt_v4(source):
    source = original_adapt(source)
    replacements = (
        ("    os.environ['SUPER_ASYNC_GENERATE_TRAJ'] = '1'\n"
         "    os.environ['SUPER_CPU_PROFILE'] =",
         "    os.environ['SUPER_ASYNC_GENERATE_TRAJ'] = '1'\n"
         "    os.environ['SUPER_STOPPED_DEPARTURE_V4'] = '1'\n"
         "    os.environ['SUPER_CPU_PROFILE'] ="),
        ("    files.update((V2_CHILD_SOURCE, V3_CHILD_SOURCE))",
         "    files.update((V2_CHILD_SOURCE, V3_CHILD_SOURCE, V4_SOURCE))\n"
         "    files.update(SOURCE / path for path in V4_CHANGED)"),
        ("                result['nearfield_async_audit'] = runtime_audit(stack)\n",
         "                result['nearfield_async_audit'] = runtime_audit(stack)\n"
         "                v4_rows = re.findall(r'\\[STOPPED_DEPARTURE_V4\\][^\\r\\n]*', stack)\n"
         "                v4_valid = len(v4_rows) == 1 and all(token in v4_rows[0] for token in (\n"
         "                    'enabled=true', 'physical_origin=true', 'prefix_from_zero=true',\n"
         "                    'shared_release=true', 'default_off=true'))\n"
         "                result['stopped_departure_v4_audit'] = dict(valid=v4_valid, records=v4_rows)\n"
         "                result['source_acquisition']['checks']['stopped_departure_v4'] = v4_valid\n"),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise ValueError('Guard-v4 child adaptation cardinality changed: ' + old)
        source = source.replace(old, new, 1)
    return source


def main():
    global original_adapt
    original_adapt = previous.adapt_main
    previous.adapt_main = adapt_v4
    try:
        generated = previous.build_main(
                install_root='/root/super_ws/scenario7_guard_v4_20260926/install')
        generated.__globals__.update(
                SOURCE=previous.SOURCE, V4_SOURCE=V4_SOURCE,
                V4_CHANGED=V4_CHANGED, re=re)
        return generated()
    finally:
        previous.adapt_main = original_adapt


if __name__ == '__main__':
    raise SystemExit(main())
