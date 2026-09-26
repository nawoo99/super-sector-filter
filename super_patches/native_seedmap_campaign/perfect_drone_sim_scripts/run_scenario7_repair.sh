#!/usr/bin/env bash
# Foreground repair-only controller; the original install is a preserved underlay.
set -e -o pipefail
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
scenario7_repair_install="${SCENARIO7_REPAIR_INSTALL:-/root/super_ws/scenario7_repair_20260926/install}"
scenario7_report_only=0
for scenario7_arg in "$@"; do
  case "$scenario7_arg" in --report|--report=*|--help|-h) scenario7_report_only=1 ;; esac
done
if [ "$scenario7_report_only" -eq 0 ]; then
  source "${scenario7_repair_install}/local_setup.bash"
fi
cd /root/super-sector-filter
export PYTHONNOUSERSITE=1
exec python3 -u /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts/run_scenario7_repair.py "$@"
