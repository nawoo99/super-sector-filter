#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
set -u
receiver_test_dir=$(mktemp -d /tmp/super_goal_receiver_metadata_XXXXXXXX)
printf 'receiver_test_dir=%s\n' "$receiver_test_dir"
receiver_build_dir=/root/super_ws/build/super_planner
read -r -a receiver_includes <<< "$(sed -n 's/^CXX_INCLUDES = //p' "$receiver_build_dir/CMakeFiles/super.dir/flags.make")"
read -r -a receiver_link_flags <<< "$(sed -n 's/.* -o fsm_node  *//p' "$receiver_build_dir/CMakeFiles/fsm_node.dir/link.txt")"
for receiver_test_name in goal_retransmit_fsm_metadata_test demand_replan_fsm_metadata_test; do
    g++ -std=c++17 -O0 -g0 -DNDEBUG -DFMT_HEADER_ONLY -DUSE_ROS2 -DORIGIN_AT_CORNER \
        '-DROOT_DIR="/root/super_ws/src/SUPER/super_planner/"' \
        "${receiver_includes[@]}" \
        -c "/root/super_ws/src/SUPER/super_planner/test/$receiver_test_name.cpp" \
        -o "$receiver_test_dir/$receiver_test_name.o"
    cd "$receiver_build_dir"
    g++ "$receiver_test_dir/$receiver_test_name.o" "${receiver_link_flags[@]}" -pthread \
        -o "$receiver_test_dir/$receiver_test_name"
done
env -u SUPER_GOAL_RETRANSMIT_IDENTITY "$receiver_test_dir/goal_retransmit_fsm_metadata_test"
env SUPER_GOAL_RETRANSMIT_IDENTITY=1 "$receiver_test_dir/goal_retransmit_fsm_metadata_test"
env -u SUPER_GOAL_RETRANSMIT_IDENTITY "$receiver_test_dir/demand_replan_fsm_metadata_test"
env SUPER_GOAL_RETRANSMIT_IDENTITY=1 "$receiver_test_dir/demand_replan_fsm_metadata_test"
