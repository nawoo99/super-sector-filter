#!/usr/bin/env bash
set -euo pipefail
cd /root/super-sector-filter/results/adaptive_cpu40_20260916/demand_replan_preflight/prototype
g++ -std=c++17 -O2 -Wall -Wextra -pedantic demand_replan_policy_test.cpp -o /tmp/demand_replan_policy_test
/tmp/demand_replan_policy_test
g++ -std=c++17 -O1 -g0 -Wall -Wextra -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer demand_replan_policy_test.cpp -o /tmp/demand_replan_policy_test_sanitize
/tmp/demand_replan_policy_test_sanitize
