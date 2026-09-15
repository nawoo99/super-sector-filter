#!/usr/bin/env bash
set -euo pipefail
# Standalone regression: compile ONE translation unit at -O0; reuse libsuper.a.
# CXX_INCLUDES is read verbatim from the existing successful package build.
backup_extra_flags=()
backup_binary_suffix=""
if [[ "${1:-native}" == "deterministic" ]]; then
  backup_binary_suffix="_deterministic"
  backup_extra_flags=(
    -DBACKUP_TEST_DETERMINISTIC_GEOMETRY
    -Wl,--wrap=_ZN14geometry_utils11enumerateVsERKN5Eigen6MatrixIdLin1ELi4ELi0ELin1ELi4EEERNS1_IdLi3ELin1ELi0ELi3ELin1EEEd
    /root/super_ws/src/SUPER/super_planner/test/backup_replay_geometry_shim.cpp
  )
fi
g++ -std=c++17 -O0 -g0 -DNDEBUG \
  -DFMT_HEADER_ONLY -DUSE_ROS2 -DORIGIN_AT_CORNER \
  '-DROOT_DIR="/root/super_ws/src/SUPER/super_planner/"' \
  $(sed -n 's/^CXX_INCLUDES = //p' /root/super_ws/build/super_planner/CMakeFiles/super.dir/flags.make) \
  /root/super_ws/src/SUPER/super_planner/test/backup_replay_equivalence_test.cpp \
  "${backup_extra_flags[@]}" \
  /root/super_ws/install/super_planner/lib/libsuper.a \
  -lyaml-cpp -ldw -pthread \
  -o "/root/super-sector-filter/results/adaptive_cpu40_20260916/backup_equivalence${backup_binary_suffix}_test"
