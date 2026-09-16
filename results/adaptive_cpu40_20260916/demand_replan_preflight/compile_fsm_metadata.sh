#!/usr/bin/env bash
set -euo pipefail
# Compile only this test TU, then reuse the actual production libraries and
# exact linked dependencies of the successful fsm_node build. Run after the
# main package build, never during a matched CPU flight.
demand_test_dir=/root/super-sector-filter/results/adaptive_cpu40_20260916/demand_replan_preflight
demand_build_dir=/root/super_ws/build/super_planner
read -r -a demand_includes <<< "$(sed -n 's/^CXX_INCLUDES = //p' "$demand_build_dir/CMakeFiles/super.dir/flags.make")"
read -r -a demand_link_flags <<< "$(sed -n 's/.* -o fsm_node  *//p' "$demand_build_dir/CMakeFiles/fsm_node.dir/link.txt")"
g++ -std=c++17 -O0 -g0 -DNDEBUG -DFMT_HEADER_ONLY -DUSE_ROS2 -DORIGIN_AT_CORNER \
  '-DROOT_DIR="/root/super_ws/src/SUPER/super_planner/"' \
  "${demand_includes[@]}" \
  -c /root/super_ws/src/SUPER/super_planner/test/demand_replan_fsm_metadata_test.cpp \
  -o "$demand_test_dir/demand_replan_fsm_metadata_test.o"
cd "$demand_build_dir"
g++ "$demand_test_dir/demand_replan_fsm_metadata_test.o" \
  "${demand_link_flags[@]}" -pthread \
  -o "$demand_test_dir/demand_replan_fsm_metadata_test"
"$demand_test_dir/demand_replan_fsm_metadata_test"
