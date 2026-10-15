#!/usr/bin/env bash
# New foreground guard-v2 cohort. Original and repair-v1 installs stay untouched.
set -e -o pipefail
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
scenario7_guard_v2_install="${SCENARIO7_GUARD_V2_INSTALL:-/root/super_ws/scenario7_guard_v2_20260926/install}"
export SCENARIO7_REPAIR_INSTALL="${scenario7_guard_v2_install}"
scenario7_guard_report_only=0
for scenario7_guard_arg in "$@"; do
  case "$scenario7_guard_arg" in --report|--report=*|--help|-h) scenario7_guard_report_only=1 ;; esac
done
if [ "$scenario7_guard_report_only" -eq 0 ]; then
  source "${scenario7_guard_v2_install}/local_setup.bash"
fi
cd /root/super-sector-filter
export PYTHONNOUSERSITE=1
exec python3 -u /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts/run_scenario7_guard_v2.py "$@"
