#!/usr/bin/env python3
"""Run the frozen v12 legacy Fixed Sector child without a mission cutoff."""
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

# Positive infinity removes only the mission-time terminal condition. Resource,
# process-integrity, and data-quality guards remain enabled.
search.OPTIONS = dict(search.OPTIONS, loop_timeout_override=float('inf'))

# With no global mission cutoff, a controller can otherwise remain forever in
# an absorbing stopped state. This observer-only terminal records failure after
# 60 seconds inside a 2 cm ball at one unreached waypoint. It does not publish
# any planner input and does not turn the event into mission success.
os.environ['SCENARIO7_TERMINAL_STALL_WINDOW_S'] = '60'
os.environ['SCENARIO7_TERMINAL_STALL_RADIUS_M'] = '0.02'

import scenario7_guard_v6_cpu_compare as runner


if __name__ == '__main__':
    raise SystemExit(runner.main())
