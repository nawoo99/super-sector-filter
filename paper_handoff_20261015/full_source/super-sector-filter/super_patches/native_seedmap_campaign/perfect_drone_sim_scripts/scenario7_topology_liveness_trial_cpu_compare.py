#!/usr/bin/env python3
"""Separate topology-recovery trial using the canonical no-cutoff protocol.

Selects only the new trial install and inventories its added source/test files.
Mission, sensing, guards, CPU flags and Active-Yaw Sector policy are inherited.
"""
from pathlib import Path

import scenario7_no_mission_cutoff_cpu_compare as no_cutoff


INSTALL_ROOT = '/root/super_ws/forest_liveness_trial_v2_20261006/install'
ADDED_INPUTS = (
    'super_planner/test/topology_recovery_liveness_test.py',
    'mars_uav_sim/perfect_drone_sim/scripts/scenario7_no_mission_cutoff_cpu_compare.py',
    'mars_uav_sim/perfect_drone_sim/scripts/scenario7_topology_liveness_trial_cpu_compare.py',
)


def main():
    v6 = no_cutoff.previous
    v5 = v6.previous
    original_install, original_inputs = v6.V6_INSTALL_ROOT, v5.V5_CHANGED
    v6.V6_INSTALL_ROOT = INSTALL_ROOT
    v5.V5_CHANGED = (*original_inputs, *ADDED_INPUTS)
    try:
        if not (Path(INSTALL_ROOT) / 'local_setup.bash').is_file():
            raise RuntimeError('Topology trial install is missing')
        for name in ('perfect_drone_full_node', 'perfect_drone_adaptive_node'):
            binary_path = Path(INSTALL_ROOT) / 'perfect_drone_sim/lib/perfect_drone_sim' / name
            binary = binary_path.read_bytes()
            for marker in (b'[TRAJ_GUARD_ZONE_DISCONNECT]',
                           b'[TRAJ_GUARD_RECOVERY_EXHAUSTED]'):
                if marker not in binary:
                    raise RuntimeError(f'Topology trial marker missing from {binary_path}: {marker!r}')
        return no_cutoff.main()
    finally:
        v6.V6_INSTALL_ROOT, v5.V5_CHANGED = original_install, original_inputs


if __name__ == '__main__':
    raise SystemExit(main())
