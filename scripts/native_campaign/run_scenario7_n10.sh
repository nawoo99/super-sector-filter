#!/usr/bin/env bash
# Foreground controller; completion returns to the existing terminal prompt.
set -e -o pipefail
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
cd /root/super-sector-filter
export PYTHONNOUSERSITE=1
exec python3 -u /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts/run_scenario7_n10.py "$@"
