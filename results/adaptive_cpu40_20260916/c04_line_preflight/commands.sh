#!/usr/bin/env bash
set -euo pipefail
cd /root/super_ws/src/SUPER

# Compile actual RayCaster, suppress only its unused common ROS/PCL utility header.
g++ -std=c++17 -O3 -Wall -Wextra -pedantic -pthread -DORIGIN_AT_CORNER -DSUPER_UTILS_HEADER_TYPE_UTILS_HPP -I/usr/include/eigen3 -Irog_map/include rog_map/test/snapshot_line_query_corpus.cpp rog_map/include/rog_map/rog_map_core/raycaster.cpp -o /tmp/snapshot_line_query_corpus
/tmp/snapshot_line_query_corpus --benchmark

# Sanitized implementation/corpus check, no benchmark under sanitizers.
g++ -std=c++17 -O1 -g0 -Wall -Wextra -pedantic -pthread -fsanitize=address,undefined -fno-omit-frame-pointer -DORIGIN_AT_CORNER -DSUPER_UTILS_HEADER_TYPE_UTILS_HPP -I/usr/include/eigen3 -Irog_map/include rog_map/test/snapshot_line_query_corpus.cpp rog_map/include/rog_map/rog_map_core/raycaster.cpp -o /tmp/snapshot_line_query_corpus_sanitize
ASAN_OPTIONS=quarantine_size_mb=32 /tmp/snapshot_line_query_corpus_sanitize
