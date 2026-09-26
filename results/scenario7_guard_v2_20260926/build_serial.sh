#!/usr/bin/env bash
# Separate repair build. Never replaces either preserved installation.
set -e -o pipefail
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
export PYTHONNOUSERSITE=1
export MAKEFLAGS='-j1 -l1'
export CMAKE_BUILD_PARALLEL_LEVEL=1
cd /root/super_ws
colcon --log-base /root/super_ws/scenario7_guard_v2_20260926/log build \
  --base-paths /root/super_ws/src/SUPER/rog_map \
    /root/super_ws/src/SUPER/super_planner \
    /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim \
  --build-base /root/super_ws/scenario7_guard_v2_20260926/build \
  --install-base /root/super_ws/scenario7_guard_v2_20260926/install \
  --packages-select rog_map super_planner perfect_drone_sim \
  --allow-overriding rog_map super_planner perfect_drone_sim \
  --executor sequential --event-handlers console_direct+ \
  --cmake-args -DCMAKE_BUILD_TYPE=Release \
  2>&1 | tee /root/super-sector-filter/results/scenario7_guard_v2_20260926/build_serial.log
