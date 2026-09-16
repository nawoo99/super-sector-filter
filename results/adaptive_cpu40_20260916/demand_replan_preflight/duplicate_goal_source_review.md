# Repeated goal receipts: C12 source/log review

Read-only review, 2026-09-16. No runtime edits or tests were performed here.
Parent authorized preparation of a separate default-off coalescing proposal;
implementation belongs to a later candidate, not the ongoing C13 simulator build.

## Actual cause

`mission_planner/data/loop24.txt` contains five waypoints, not 24 goals.
`mission_planner/launch/benchmark_seedmap.launch.py:79–85` starts the mission
with **waypoint.yaml**, whose `publish_dt` is 1.0 seconds. The similarly named
`waypoint_repeat_1hz.yaml` also exists but is not this launch's selected file.
`ros2_waypoint_planner.hpp:142–154` republishes the current target with a fresh
header stamp on that period, as well as immediately when changing waypoints.

The FSM treats every receipt as a fresh goal:

- `fsm_ros2.hpp:3276–3280` extracts raw position/quaternion, currently discards
  headers, and calls `enqueueGoal`.
- `fsm.cpp:258–266` replaces the latest pending slot and always increments the
  queued revision.
- `fsm.cpp:269–335` consumes the request, applies click-height and nearest-free
  projection, installs the target, sets `gi_.new_goal=true`, and increments the
  accepted revision through `GoalUpdateScope`.
- Demand's `sameGoalDemand` therefore no longer matches the previous own-commit
  lease. `NEW_GOAL` bypasses deferral even when requested target coordinates
  repeat.
- The ordinary solver receives `new_goal=true`; `generateExpTraj` at
  `super_planner.cpp:2910` and `2927` conditions its goal-connected and near-goal
  no-new-EXP exits on `!gi_.new_goal`. Repeated receipts can cause real new EXP
  and backup work rather than merely an inexpensive NO_NEED return.

## C12 log quantification

Source logs are `c12_extended_lease_profile/artifacts/seed1_run9313_{mode}.attempt1.stack.log`.
Counts below use accepted `Receive click goal at:` records after stripping ANSI
formatting. Printed mapped positions were normalized to six decimal places
only for this descriptive log count, **not** as a proposed deduplication rule.

| Observation | Full | Adaptive |
| --- | ---: | ---: |
| Accepted goal log records | 40 | 41 |
| Consecutive distinct target groups | 5 | 5 |
| Same-target adjacent repeat receipts | 35 | 36 |
| ReplanOnce/with_backup own commit logs | 122 | 123 |
| ReplanOnce/no_backup own commit logs | 16 | 14 |
| PlanFromRest/with_backup commit logs | 1 | 2 |
| Final available NEW_GOAL decision count | 43 | 38 |

Accepted targets, in order, are the five projected locations
`[24.025,24.025,1.525]`, `[-23.975,24.025,1.525]`,
`[-23.975,-23.975,1.525]`, `[24.025,-23.975,1.525]`, and
`[0.025,0.025,1.525]`. Full receipt counts per target are 7/10/8/9/6;
Adaptive counts are 7/9/10/8/7.

Each of the 35/36 repeated accepted records is followed in the same stack log by
at least one `ReplanOnce` commit before the next accepted goal. Example Full:
receipt line510 -> generation6 commit line513; line555 -> generation10 line559;
line603 -> generation13 line606. Adaptive: line503 -> generation4 line519;
line536 -> generation6 line537; line582 -> generation10 line585.

This is a line-order association, not per-receipt optimizer CPU attribution or
proof that every intervening commit was caused by the repeated goal. The
histogram stops at its final available five-second report and also counts
pending/updated goal mismatches, so it need not equal total receipts.
Nevertheless, together with the source behavior, this is a meaningful
optimization candidate rather than a PlanFromRest/cheap-no-op-only artifact.
Actual saved CPU requires a matched common Full/Adaptive ablation.

## Narrow future contract and caveats

- Do not alter mission publication cadence/QoS, risking loss of a first goal.
- Exact opt-in only. Compare original finite raw xyz and all four quaternion
  coefficients exactly, plus retained raw frame/source-command identity. Never
  compare with `gi_.goal_p`, which is projected and later remapped again by
  `callReplanOnce` at `fsm.cpp:86`; do not use voxel/epsilon/yaw-only equality or
  normalize quaternion/sign representations to enlarge matches.
- Preserve every changed coordinate/orientation/frame, nonfinite input, pending
  different goal, pending goal update, and retry while stopped, recovering,
  blocked, not following, on backup, finished, or otherwise uncertified.
- Suppression requires a mutex-protected token from the exact accepted request
  and a successful *own ordinary* commit. Preserve current goal revisions,
  lifecycle epoch, current committed generation and immutable-map explicit-SAFE
  proof. Direct reads of callback-owned `demand_*` fields from the goal callback
  would be a data race; a separate synchronized token is required.
- Suppressing a duplicate must not bump queued/accepted revisions, set NEW_GOAL,
  refresh/extend the dispatch lease, consume recovery state, clear safety flags,
  or drop a pending different request. Every fallback uses normal enqueue.
- A FOLLOW -> EMER_STOP -> FOLLOW lifecycle ABA must invalidate old eligibility.
  Do not prove absence of intervening recovery with two loose atomic snapshots.
  Audit enqueue transaction lock order against activation, refresh and safety
  locks before adding synchronization.

Two semantic limitations need explicit treatment in the future proposal:

1. PoseStamped contains no explicit heartbeat/retry intent ID. Fresh stamps are
   used by the mission heartbeat and are ignored by the current FSM. Identical
   raw pose cannot distinguish that heartbeat from a deliberate healthy-state
   retry. The opt-in must define repeated identical commands as idempotent only
   under its narrowly certified eligibility, or introduce an explicit intent
   protocol; do not claim an intent distinction that the message lacks.
2. Reacceptance redoes raw-to-nearest-free projection. Projection may change as
   the map changes, and the effective target can also remap during ordinary
   planning. Exact behavior equivalence requires preserving/checking projection
   equivalence to the current effective target; otherwise describe the change
   honestly as an idempotent-command algorithm change, not a no-op refactor.

Required tests include exact finite matches and one-component/frame changes,
NaNs/infinities, raw-z differences despite fixed click height, pending B then
incoming A, B arriving during A acceptance/commit, no-own-commit/FINISH cases,
rejection/recovery/failure after prior success, lifecycle ABA, and concurrent
mixed requests. Extend the existing actual-FSM metadata seam, but do not claim
it proves live map-projection equivalence without a map-backed fixture.
