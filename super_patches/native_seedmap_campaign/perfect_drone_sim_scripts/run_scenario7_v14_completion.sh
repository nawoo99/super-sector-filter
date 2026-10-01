#!/usr/bin/env bash
# Resume c40 only in the separate completion archive; original flights stay immutable.
set -e -o pipefail
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
cd /root/super-sector-filter
export PYTHONNOUSERSITE=1
exec python3 -u \
  /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts/run_scenario7_v14_completion.py "$@"
