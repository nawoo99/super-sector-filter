# Two-phase static-PC polling candidate (proposal only)

Status: outside-runtime prototype prepared during frozen C12 compilation. Not
applied, compiled, or flown. Do not adopt without C12 profiling identifying
material static-callback/executor overhead and parent approval.

## Contract

- Default remains legacy 1 ms. New exact opt-in is
  `SUPER_STATIC_PC_TWO_PHASE=1`; it rejects combination with the earlier rejected
  `SUPER_STATIC_PC_POLL_MS=100` mode. Unset/0 does nothing.
- Preserve the existing publication function literally: same node-clock
  `cur_t > 5.0 && cur_t < 5.1` burst window, subscriber-count state, complete map
  payload, QoS, renderer getter/conversion, and publication rules. This is NOT the
  earlier steady-time once-only bootstrap candidate.
- A fast wrapper invokes that function on the existing 1 ms timer. Only after an
  executed legacy callback sees node-relative time at/after 5.1 s is the fast timer
  canceled. A simultaneously due/queued fast callback is guarded at entry.
- A second 100 ms timer exists only when opted in, in the SAME mutually-exclusive
  global-PC group. It performs no graph query/publication while fast mode is
  active; after handoff it invokes the exact same legacy function/state. No new
  executor or thread is introduced. Slow-before-fast and fast-before-slow ordering
  cannot duplicate the legacy bootstrap condition or drop the last fast tick's
  subscriber-count check.
- Postbootstrap count-change detection is nominally within one 100 ms poll period
  PLUS executor/serialization delay. Neither a hard100ms bound nor DDS delivery
  is guaranteed. Rapid disconnected/reconnected readers with the same sampled
  count can be missed, as in legacy, with a larger observation interval.
- Stable node-clock operation is the supported optimization case. Simulated ROS
  time active, negative/nonfinite elapsed time, or an observed backward jump
  permanently restores legacy 1 ms polling and logs the reason. It does not
  migrate bootstrap semantics to steady time. Arbitrary clock changes between
  coarse samples cannot be detected immediately; exact original publication
  opportunities around such a jump are NOT guaranteed. No claim of hard-time
  clock safety is made. Ordinary benchmark uses stable node/system time.

During opt-in fast startup the extra slow timer adds only 10 short gated callbacks
per second and the fast callback adds a node-clock policy check. Counts of actual
bootstrap publications remain load-dependent: never promise a fixed 19 sends.
After handoff the fast timer is genuinely canceled, not a1kHz early-return loop.
Existing SimStaticCloud profiling scopes remain around the unchanged publication
function; tiny wrapper phase checks/gated slow callbacks are not included in that
stage, but remain in measured whole-process CPU.

## Files / pure tests

- `static_pc_two_phase_policy.hpp`: exact opt-in parser, stable-clock phase state,
  one-way permanent clock fallback; no ROS dependency.
- `static_pc_two_phase_policy_test.cpp`: parser/conflict, disabled compatibility,
  scripted bootstrap boundaries, handoff count change, simultaneously due timers,
  queued-fast guard, unchanged subscriber state, disconnect/reconnect, and clock
  fallback. This simulates dispatch; it is not evidence of actual ROS cadence.
- `ros2_perfect_drone_model.hpp`: staged binding over current C12 runtime.
- `static_pc_late_subscriber_test.py`: existing no-flight ROS harness extended
  with opt-in/sequence/hash options, preserving legacy controls and error reports.

After authorization, compile pure test optimized + ASan/UBSan. Do not compile or
run during frozen flight. Applying the proposal requires changing the pure-test
include to `<perfect_drone_sim/static_pc_two_phase_policy.hpp>` (runtime patch
already does so). No planner/guard/acquisition/odometry/render timer is changed.

## ROS smoke matrix (not yet run)

Use a distinct unused ROS_DOMAIN_ID, normal renderer display, and sourced ROS/
workspace. Paths below are placeholders for unique new artifact directories.

```sh
python3 static_pc_late_subscriber_test.py --poll-ms 1 --sequence reader-first --out-dir CONTROL_READER_FIRST
python3 static_pc_late_subscriber_test.py --poll-ms 1 --two-phase --sequence reader-first --expected-sha256 CONTROL_HASH --out-dir CANDIDATE_READER_FIRST
python3 static_pc_late_subscriber_test.py --poll-ms 1 --sequence late --out-dir CONTROL_LATE
python3 static_pc_late_subscriber_test.py --poll-ms 1 --two-phase --sequence late --expected-sha256 CONTROL_HASH --out-dir CANDIDATE_LATE
```

Each sequence goes on to second-reader join, count decrease2→1, complete
disconnect1→0, and reconnect0→1. Every received payload must retain the full
point count/frame/layout/bytes, one within-run geometrySHA, and optional exact
legacy controlSHA. Default seed1 expected point count is241490, as before.
Reader-first is created BEFORE simulator startup; late reader joins only after
the no-listener bootstrap window/handoff. Inspect both successful phases and
the first failed transition, not only the aggregate valid flag.
Each callback immediately validates/persists payload/layout/hash evidence;
`reader_first_geometry_valid` and `reader_first_geometry_sha256` remain available
even if a subsequent transition fails. Such a later failure still leaves the
whole test `valid=false`; phase success is never relabeled as whole-test success.

Known unresolved infrastructure issue: legacy late large best-effort clouds
previously produced publication logs without delivery. This proposal does not
change QoS, inject retries, or silently count publication as receipt. If it
recurs, retain/report the failed legacy and candidate runs separately; do not
claim late/reconnect reliability fixed or mark their tests passed. Startup
reader-first and an actual matched flight/monitor-ready audit are mandatory before
any performance adoption. No sysctl/network tuning is authorized here.
