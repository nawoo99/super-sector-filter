#!/usr/bin/env python3
"""V5 opt-in stopped polyline recovery; no capture/fault hooks in pilot."""
import os
from pathlib import Path
import scenario7_topology_liveness_trial_cpu_compare as v2


def main():
    for key, value in os.environ.items():
        if key.startswith('SUPER_TEST_') and value not in ('', '0'):
            raise RuntimeError('Pilot forbids test fault hooks: '+key)
    if os.environ.get('SUPER_PLANNER_FAILURE_CAPTURE_DIR'):
        raise RuntimeError('Diagnostic capture must be OFF in performance pilot')
    os.environ['SUPER_CERTIFIED_POLYLINE_RECOVERY'] = '1'
    old_install, old_inputs = v2.INSTALL_ROOT, v2.ADDED_INPUTS
    v2.INSTALL_ROOT = '/root/super_ws/forest_liveness_trial_v5_20261006/install'
    for name in ('perfect_drone_full_node', 'perfect_drone_adaptive_node'):
        binary = Path(v2.INSTALL_ROOT)/'perfect_drone_sim/lib/perfect_drone_sim'/name
        if b'[TRAJ_GUARD_POLYLINE_RECOVERY]' not in binary.read_bytes():
            raise RuntimeError('V5 recovery marker missing: '+str(binary))
    v2.ADDED_INPUTS = (*old_inputs,
        'mars_uav_sim/perfect_drone_sim/scripts/scenario7_topology_liveness_v5_cpu_compare.py',
        'super_planner/src/super_core/certified_polyline_recovery.cpp',
        'super_planner/include/super_core/planner_failure_capture.hpp',
        'rog_map/include/rog_map/rog_map.h', 'rog_map/src/rog_map/rog_map.cpp')
    try:
        return v2.main()
    finally:
        v2.INSTALL_ROOT, v2.ADDED_INPUTS = old_install, old_inputs


if __name__ == '__main__':
    raise SystemExit(main())
