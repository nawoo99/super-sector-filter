#!/usr/bin/env python3
"""Run the canonical Active-Yaw Sector without a mission-time cutoff."""
from pathlib import Path
import os
import sys


REPO_SCRIPTS = Path('/root/super-sector-filter/scripts/native_campaign')
SUPER_SCRIPTS = Path(
    '/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts'
)
sys.path.insert(0, str(REPO_SCRIPTS))
sys.path.insert(0, str(SUPER_SCRIPTS))

import cylinder_map_search as search


search.OPTIONS = dict(search.OPTIONS, loop_timeout_override=float('inf'))
os.environ['SCENARIO7_TERMINAL_STALL_WINDOW_S'] = '60'
os.environ['SCENARIO7_TERMINAL_STALL_RADIUS_M'] = '0.02'

# This is the canonical entrypoint.  Its preflight now requires the Active-Yaw
# binary and makes mode=sector enable both Active-Yaw and empty-scan heartbeat.
import scenario7_guard_v6_cpu_compare as runner


if __name__ == '__main__':
    raise SystemExit(runner.main())
