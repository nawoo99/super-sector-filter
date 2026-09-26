#!/usr/bin/env python3
"""Diagnostic v5 child: v4 plus a fully checked stationary soft-margin hold."""
from pathlib import Path
import re

import scenario7_guard_v4_cpu_compare as previous


V5_SOURCE = Path(__file__).resolve()
V5_INSTALL_ROOT = '/root/super_ws/scenario7_guard_v5_20260927/install'
V5_CHANGED = (
    'super_planner/include/ros_interface/ros2/fsm_ros2.hpp',
    'super_planner/test/stopped_hold_v5_source_contract_test.py',
)


def adapt_v5(source):
    source = original_adapt(source)
    replacements = (
        ("    os.environ['SUPER_STOPPED_DEPARTURE_V4'] = '1'\n"
         "    os.environ['SUPER_CPU_PROFILE'] =",
         "    os.environ['SUPER_STOPPED_DEPARTURE_V4'] = '1'\n"
         "    os.environ['SUPER_STOPPED_HOLD_V5'] = '1'\n"
         "    os.environ['SUPER_CPU_PROFILE'] ="),
        ("    files.update((V2_CHILD_SOURCE, V3_CHILD_SOURCE, V4_SOURCE))",
         "    files.update((V2_CHILD_SOURCE, V3_CHILD_SOURCE, V4_SOURCE, V5_SOURCE))\n"
         "    files.update(SOURCE / path for path in V5_CHANGED)"),
        ("                result['source_acquisition']['checks']['stopped_departure_v4'] = v4_valid\n",
         "                result['source_acquisition']['checks']['stopped_departure_v4'] = v4_valid\n"
         "                v5_rows = re.findall(r'\\[STOPPED_HOLD_V5\\][^\\r\\n]*', stack)\n"
         "                v5_valid = len(v5_rows) == 1 and all(token in v5_rows[0] for token in (\n"
         "                    'enabled=true', 'stationary_only=true',\n"
         "                    'deferred_soft_margin=true', 'hard_checks_required=true',\n"
         "                    'default_off=true'))\n"
         "                result['stopped_hold_v5_audit'] = dict(valid=v5_valid, records=v5_rows)\n"
         "                result['source_acquisition']['checks']['stopped_hold_v5'] = v5_valid\n"),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise ValueError('Guard-v5 child adaptation cardinality changed: ' + old)
        source = source.replace(old, new, 1)
    return source


def main():
    global original_adapt
    original_adapt = previous.adapt_v4
    previous.adapt_v4 = adapt_v5
    try:
        # v4 main delegates through v3 build_main, so replace its adapter and
        # invoke it normally. Its fixed install root is replaced in the
        # generated source before execution below.
        original_build_main = previous.previous.build_main

        def build_main_v5(*args, **kwargs):
            kwargs['install_root'] = V5_INSTALL_ROOT
            generated = original_build_main(*args, **kwargs)
            generated.__globals__.update(
                    V5_SOURCE=V5_SOURCE, V5_CHANGED=V5_CHANGED)
            return generated

        previous.previous.build_main = build_main_v5
        try:
            return previous.main()
        finally:
            previous.previous.build_main = original_build_main
    finally:
        previous.adapt_v4 = original_adapt


if __name__ == '__main__':
    raise SystemExit(main())
