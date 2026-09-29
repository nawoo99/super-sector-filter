#!/usr/bin/env python3
"""Run the frozen Active-Yaw Sector child without a mission-time cutoff."""
from pathlib import Path
import sys


REPO_SCRIPTS = Path('/root/super-sector-filter/scripts/native_campaign')
SUPER_SCRIPTS = Path('/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts')
sys.path.insert(0, str(REPO_SCRIPTS))
sys.path.insert(0, str(SUPER_SCRIPTS))

import cylinder_map_search as search

# The native monitor treats positive infinity as an always-open mission-time
# horizon. Resource and process-integrity guards remain enabled.
search.OPTIONS = dict(search.OPTIONS, loop_timeout_override=float('inf'))

import scenario7_active_yaw_scan_v1_cpu_compare as runner


if __name__ == '__main__':
    raise SystemExit(runner.main())
