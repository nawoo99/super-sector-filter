# Async ordinary GENERATE_TRAJ: bounded offline validation

Date: 2026-09-26. Source frozen for the coordinator's prospective overlay build
attempt 2, after the independent review corrections below.
This is implementation/offline evidence, not a successful flight or CPU result.

## Scope

`SUPER_ASYNC_GENERATE_TRAJ=1` is a separate opt-in, default off. It dispatches
ordinary `PlanFromRest` through the existing replan executor. Main retains the
hold, goal/ACK/revision admission, current-map certificate checks and final
publication. No A* budget, geometry/radius, unknown-space predicate or timing
threshold was changed. Ordinary generation does not implicitly request Full.

Internally committed candidates remain quarantined across result discard.
Normal command, polynomial and brake-fallback selection respect this gate.
Initial generation-zero startup does not fabricate a previous trajectory
command. A two-thread policy test models a goal revision changing during
computation, stale receipt rejection, retained quarantine and later dispatch.

Final ordinary release compares the pinned held PVA against the candidate at
the same final publication wall time, under the safety publication lock, using
the existing trajectory-handoff tolerances: position 0.001 m, velocity 0.01 m/s,
acceleration 0.1 m/s^2. It also requires fresh finite odometry with speed at most
0.05 m/s from the separate ROS2 `getLatestOdomTwist` receive sample, not the
legacy pose-only `RobotState.v`. No outgoing-only timestamp rebase or tolerance relaxation is used.
Rejected P/V/A deltas are logged by `ASYNC_GENERATE_HANDOFF_REJECT`. A delayed
ordinary command additionally rechecks exact generation/start clock and current
certificate/map/checked interval under the final safety publication lock.

## Independent review corrections before build attempt 2

The first offline snapshot passed its then-ten source contracts and normal/
sanitized helper tests, but the independent reviewer found two real source-level
gaps. Those original passes are not evidence against the findings:

1. `ROGMap::RobotState.v` stays zero because the legacy map state update is
   pose-only. The original finite/speed check was vacuous. Both initial dispatch
   and retained-hold validation now read `getLatestOdomTwist`, reject unavailable,
   nonfinite, future or older-than-0.1-second receipts and speeds above 0.05 m/s.
   Receipt and `getSimTime()` use the same ROS node clock.
2. A precomputed ordinary command could span FOLLOW → quarantine → accepted
   FOLLOW and pass a state-only publication gate after a newer path was released.
   The final safety-locked transaction now rejects a sampled generation/start
   mismatch and stale certificate/map/interval. It does not invalidate a valid
   new certificate merely because an old delayed command lost the race.

The coordinator interrupted build attempt 1 for review (exit 143 after process
termination, not a compiler failure); its log is preserved separately as
`build_all_attempt1_review_interrupted.log`. The six-file identity table below
supersedes the first snapshot. In that first snapshot `fsm_ros2.hpp` was
`a4c49dc07c688af4a3e14adac61b2ea31efe265793c84c065736110d01a581d5`, the helper
was `d42bd5139f94263d9e70e53ca66a1f7e0014f12a02b57d96b6482588690b831b`, the C++
test was `fc590b4d6e81b45ae3f9b66022225f4bb3d47d31f4016e382edac1009ac9a9e8`, and
the Python test was `cfdce321996211a231d64a6806221de547a84f485be4968a2b278ca3b23ccd90`.

## Test execution

All commands exited zero after both review corrections:

```text
g++ -std=c++17 -O1 -Wall -Wextra -pthread -I<runtime>/super_planner/include
    <runtime>/super_planner/test/async_from_rest_planning_test.cpp -o <evidence>/policy
<evidence>/policy
async_from_rest_planning_test: PASS

g++ [same flags] -fsanitize=address,undefined -fno-omit-frame-pointer
    <runtime>/super_planner/test/async_from_rest_planning_test.cpp -o <evidence>/policy_sanitized
<evidence>/policy_sanitized
async_from_rest_planning_test: PASS

python3 <runtime>/super_planner/test/async_from_rest_source_contract_test.py
Ran 12 tests in 0.040s
OK
```

`<runtime>` is `/root/super_ws/src/SUPER`; `<evidence>` is this report's sibling
`async_generate_tests` directory. The sanitized executable emitted no sanitizer
diagnostic. This is ASan/UBSan, not a ThreadSanitizer or real ROS concurrency test.

The policy tests exercise exact request/ACK/goal/hold identities, all release
proof fields, stale publication, exact raw goal replay versus changed creation
stamp/frame/pose/orientation or a drained request, and the actual shared
`trajectory_handoff::compareAt` helper with position/velocity/acceleration and
NaN rejection. Additional tests cover unavailable/future/stale/moving/nonfinite
twist and a deterministic two-thread delayed-ordinary-sample ABA interleaving,
plus generation/start/certificate/range rejection. The twelve Python tests assert production source wiring and lock/
gate placement; they do not execute the ROS callbacks or prove race freedom.

## Runtime/mirror identities at freeze

All six corresponding runtime and mirror SHA-256 digests match. Paths below
are relative to `super_planner/`; mirror mapping is the project's existing
`super_planner_include`, `super_planner_src`, `super_planner_test` convention.

| File | SHA-256 |
|---|---|
| `include/fsm/fsm.h` | `1e944a48dc8cacc152d5d0e0542fd2c8bcb4b3efbdfe0975f0b505d49960678d` |
| `src/super_core/fsm.cpp` | `22352f9d291302ea7c3b3ce1aba330d054a61843d3fdf96e4f68bcc9ccccf6ce` |
| `include/ros_interface/ros2/fsm_ros2.hpp` | `eda99ea586ef6c464322b3c6f52da4d10771677d28b2e428ae018a32dd57cb37` |
| `include/fsm/async_from_rest_planning.hpp` | `5666247a266f930f4485db88b2a34f2faf99ece6efbc6edbd7d7934e4adeb03f` |
| `test/async_from_rest_planning_test.cpp` | `e7326136f5d1919ca897725abdd1ea1a9a1d0ccba50702fe49bcaca45eee74ab` |
| `test/async_from_rest_source_contract_test.py` | `fef98505b188fd425a4a3b71e800ef5394e8df0985b643da68b705f53adc8e32` |

## Important unresolved limits

The new conservative gate applies only to ordinary async generation. Existing
certified emergency recovery still uses its previous stopped-release policy;
it does not yet use this held-to-candidate PVA comparison. An ordinary failure
can trigger that existing recovery path. Therefore this patch does **not**
establish continuous handoff for every stopped departure.

The planner timestamps a from-rest candidate at solve start. Main may receive a
candidate already moving at result-finalization time. The new gate can reject
such candidates indefinitely: liveness has not been established. That is a
prospective smoke question, not grounds for loosening a safety threshold.

Other main-loop geometric checks may still take longer than 10 ms. This change
does not guarantee callback frequency, contact-free flight, strict-known-free
space, or performance improvement. ROS compilation and prospective flight
audits are coordinator-owned and must be reported separately.
