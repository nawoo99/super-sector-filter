#!/usr/bin/env bash
# Fresh seven-map common campaign after the bounded recovery repair.
set -e -o pipefail
source /opt/ros/humble/setup.bash
source /root/super_ws/sector_active_yaw_scan_v1_20260929/install/setup.bash
cd /root/super-sector-filter
export PYTHONNOUSERSITE=1

scenario7_v13_output="${SCENARIO7_V13_OUTPUT:-/root/super-sector-filter/results/scenario7_bounded_recovery_v13_n10_20260930}"
exec python3 -u \
  /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts/run_scenario7_v13_n10.py \
  --output "${scenario7_v13_output}" "$@"
