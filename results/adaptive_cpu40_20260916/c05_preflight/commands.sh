#!/usr/bin/env bash
set -euo pipefail
cd /root/super_ws/src/SUPER

# Reviewed prototype was promoted into the package after the C4 source freeze.
cache_corpus=rog_map/test/snapshot_neighborhood_cache_corpus.cpp
g++ -std=c++17 -O3 -Wall -Wextra -pedantic -pthread -DORIGIN_AT_CORNER -DSUPER_UTILS_HEADER_TYPE_UTILS_HPP -I/usr/include/eigen3 -Irog_map/include "$cache_corpus" rog_map/include/rog_map/rog_map_core/raycaster.cpp -o /tmp/snapshot_neighborhood_cache_corpus
/tmp/snapshot_neighborhood_cache_corpus --benchmark

g++ -std=c++17 -O1 -g0 -Wall -Wextra -pedantic -pthread -fsanitize=address,undefined -fno-omit-frame-pointer -DORIGIN_AT_CORNER -DSUPER_UTILS_HEADER_TYPE_UTILS_HPP -I/usr/include/eigen3 -Irog_map/include "$cache_corpus" rog_map/include/rog_map/rog_map_core/raycaster.cpp -o /tmp/snapshot_neighborhood_cache_corpus_sanitize
ASAN_OPTIONS=quarantine_size_mb=32 /tmp/snapshot_neighborhood_cache_corpus_sanitize
