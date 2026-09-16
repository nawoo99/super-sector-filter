# Plan A implementation status

2026-09-16: explicitly authorized global-PC-only Plan A is now applied
to runtime and mirrored. Optimized and ASan/UBSan pure tests passed19checks each;
root subsequently completed the combined simulator build. After explicit
authorization, this agent completed six no-flight ROS arms. Legacy-reader
compatibility FAILED for the candidate; keep its flag0. Durable-reader
diagnostics passed separately. See `ROS_FINDINGS.md` for the preserved matrix.
Plan B remains an outside-runtime proposal; it was not applied.

Owned files under `mars_uav_sim/perfect_drone_sim/`:

- `include/perfect_drone_sim/ros2_perfect_drone_model.hpp`
- `include/perfect_drone_sim/static_pc_durable_policy.hpp` (new)
- `test/static_pc_durable_policy_test.cpp` (new)
- `test/static_pc_late_subscriber_test.py`

All mirror copies use the corresponding
`super_patches/native_seedmap_campaign/mars_uav_sim_perfect_drone_sim/` paths.

`SUPER_STATIC_PC_DURABLE` accepts unset/0 (legacy), exact1 (candidate); other
values reject startup. Candidate rejects static100 or two-phase combinations
before renderer construction. Only the `/global_pc` publisher changes to
Reliable/TransientLocal/KeepLast1 with intra-process explicitly disabled.
Every existing publication body, count-edge condition, timer, ROS-time
bootstrap window, local sensor/odom/command QoS remains unchanged. The
`STATIC_PC_POLL_SETTINGS` marker truthfully reports `qos_unchanged=0` only when
durable mode is active; a dedicated durable marker records both enabled and
disabled effective settings. C15 performance run must explicitly set durable0.

## Checks performed so far

- Read-only comparison against prior mirrored model: only the scoped QoS branch,
  parser ordering, one bool and markers changed.
- Python fixture AST parse passed.
- With subsequent explicit approval, pure C++ optimized and ASan/UBSan tests
  passed19checks each, exit0. Compile and test logs are preserved beside this
  note. Binaries are outside the repository at `/tmp/static-pc-durable-tests.KBhqUO/`.
- Six actual no-flight ROS arms subsequently ran once each, all cleanexit0.
  No flight or CPU-saving claim was performed by this test.

## Reproduction command history (matrix completed; no rerun authorized)

Pure helper test (19 checks passed optimized and ASan/UBSan):

```sh
g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic -I/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/include /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_durable_policy_test.cpp -o /tmp/static_pc_durable_policy_test
/tmp/static_pc_durable_policy_test
```

The sanitizer run used `-O1 -g -fsanitize=address,undefined
-fno-omit-frame-pointer`, the same warning flags, and
`ASAN_OPTIONS=detect_leaks=1`. All four compile/test commands exited0.

Use unique artifact directories for each following attempt and the established
working renderer display. Script now executes the installed simulator binary
directly (no ros2-run/launch forwarding), hard-requires domain190, bounds useful
work to90s plus bounded8+3+3s cleanup, and rejects nonzero/forced child exits.
It never auto-retries or overwrites an existing result/log.

```sh
ROS_DOMAIN_ID=190 /usr/bin/python3 /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py --poll-ms 1 --reader-qos legacy --sequence reader-first --out-dir CONTROL_READER_FIRST
ROS_DOMAIN_ID=190 /usr/bin/python3 /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py --poll-ms 1 --durable --reader-qos legacy --sequence reader-first --expected-sha256 BASELINE_SHA --out-dir DURABLE_LEGACY_READER_FIRST
ROS_DOMAIN_ID=190 /usr/bin/python3 /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py --poll-ms 1 --durable --reader-qos legacy --sequence late --expected-sha256 BASELINE_SHA --out-dir DURABLE_LEGACY_LATE
ROS_DOMAIN_ID=190 /usr/bin/python3 /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py --poll-ms 1 --durable --reader-qos durable --sequence reader-first --expected-sha256 BASELINE_SHA --out-dir DURABLE_READERS_FIRST
ROS_DOMAIN_ID=190 /usr/bin/python3 /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py --poll-ms 1 --durable --reader-qos durable --sequence late --expected-sha256 BASELINE_SHA --out-dir DURABLE_READERS_LATE
```

The controls may retain their known later-phase failure: a successful initial
full geometry observation can supply the exact baseline SHA without declaring
that whole control passed. Candidate tests require the baseline SHA and check
actual discovered publisher QoS, not just requested environment or log text.
Each full sequence covers initial/late first reader, second reader, count
decrease and disconnect/reconnect; every received payload/layout is checked.
Source cadence acceptance is9.5–10.5Hz (not relaxed). Failed phases stay failed;
durable-reader success cannot substitute for unchanged legacy-reader failure.
