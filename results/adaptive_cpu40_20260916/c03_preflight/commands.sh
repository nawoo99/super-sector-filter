#!/usr/bin/env bash
set -euo pipefail
cd /root/super_ws/src/SUPER

# Standalone synthetic ordered-output corpus and whole-query CPU benchmark.
g++ -std=c++17 -O3 -Wall -Wextra -pedantic -Irog_map/include rog_map/test/occupied_box_scan_corpus.cpp -o /tmp/occupied_box_scan_corpus
/tmp/occupied_box_scan_corpus --benchmark

# Standalone sanitizer corpus. Quarantine is bounded to keep memory modest.
g++ -std=c++17 -O1 -g0 -Wall -Wextra -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Irog_map/include rog_map/test/occupied_box_scan_corpus.cpp -o /tmp/occupied_box_scan_corpus_sanitize
ASAN_OPTIONS=quarantine_size_mb=32 /tmp/occupied_box_scan_corpus_sanitize
