#!/usr/bin/env python3
"""V4: one fresh connected-topology query, canonical mission/guards unchanged."""
import os
from pathlib import Path
import scenario7_topology_liveness_trial_cpu_compare as v2


def main():
    for key, value in os.environ.items():
        if key.startswith('SUPER_TEST_') and value not in ('', '0'):
            raise RuntimeError('Canonical confirmation forbids test fault hooks: ' + key)
    old_install, old_inputs = v2.INSTALL_ROOT, v2.ADDED_INPUTS
    v2.INSTALL_ROOT = '/root/super_ws/forest_liveness_trial_v4_20261006/install'
    for name in ('perfect_drone_full_node', 'perfect_drone_adaptive_node'):
        binary = Path(v2.INSTALL_ROOT) / 'perfect_drone_sim/lib/perfect_drone_sim' / name
        if b'[TRAJ_GUARD_CONNECTED_RETRY]' not in binary.read_bytes():
            raise RuntimeError('V4 fresh-query marker missing: ' + str(binary))
    v2.ADDED_INPUTS = (*old_inputs,
        'mars_uav_sim/perfect_drone_sim/scripts/scenario7_topology_liveness_v4_cpu_compare.py',
        'mars_uav_sim/perfect_drone_sim/scripts/forest_stopped_topology_diagnostic.py',
        'mars_uav_sim/perfect_drone_sim/config/forest_stopped_diagnostic_20261006.yaml')
    try:
        return v2.main()
    finally:
        v2.INSTALL_ROOT, v2.ADDED_INPUTS = old_install, old_inputs


if __name__ == '__main__':
    raise SystemExit(main())
