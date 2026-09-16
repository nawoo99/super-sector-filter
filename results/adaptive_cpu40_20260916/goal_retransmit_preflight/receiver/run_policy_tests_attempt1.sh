#!/usr/bin/env bash
set -euo pipefail
receiver_test_dir=$(mktemp -d /tmp/super_goal_receiver_policy_XXXXXXXX)
printf 'receiver_test_dir=%s\n' "$receiver_test_dir"
receiver_runtime=/root/super_ws/src/SUPER/super_planner
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
    -I"$receiver_runtime/include" "$receiver_runtime/test/goal_retransmit_policy_test.cpp" \
    -o "$receiver_test_dir/goal_retransmit_policy_test_optimized"
"$receiver_test_dir/goal_retransmit_policy_test_optimized"
g++ -std=c++17 -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined \
    -Wall -Wextra -Werror -I"$receiver_runtime/include" \
    "$receiver_runtime/test/goal_retransmit_policy_test.cpp" \
    -o "$receiver_test_dir/goal_retransmit_policy_test_sanitized"
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$receiver_test_dir/goal_retransmit_policy_test_sanitized"
