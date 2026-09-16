#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
export CMAKE_BUILD_PARALLEL_LEVEL=1
export MAKEFLAGS=-j1
receiver_build_log=/root/super-sector-filter/results/adaptive_cpu40_20260916/goal_retransmit_preflight/receiver/build_attempt1.log
if test -e "$receiver_build_log"; then
    echo 'Refusing to overwrite existing receiver build attempt log.' >&2
    exit 2
fi
cd /root/super_ws
colcon build --packages-select super_planner perfect_drone_sim \
    --executor sequential --parallel-workers 1 \
    --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
    --event-handlers console_direct+ 2>&1 | tee "$receiver_build_log"
