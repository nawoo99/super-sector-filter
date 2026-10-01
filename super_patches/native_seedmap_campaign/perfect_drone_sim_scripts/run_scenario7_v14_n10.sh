#!/usr/bin/env bash
# Fresh no-mission-cutoff seven-map campaign; never overwrites the c39 archive.
set -e -o pipefail
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
cd /root/super-sector-filter
export PYTHONNOUSERSITE=1

scenario7_v14_output="${SCENARIO7_V14_OUTPUT:-/root/super-sector-filter/results/scenario7_no_mission_cutoff_v14_n10_20261001}"
exec python3 -u \
  /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts/run_scenario7_v14_n10.py \
  --output "${scenario7_v14_output}" "$@"
