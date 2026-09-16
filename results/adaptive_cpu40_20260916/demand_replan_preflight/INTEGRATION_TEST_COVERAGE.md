# Guarded demand-replan preflight coverage

## Executed against the built production library

`super_planner/test/demand_replan_fsm_metadata_test.cpp` is a derived Fsm probe
linked against the rebuilt real `libsuper.a` and the node's real dependencies.
The compile/run script is `compile_fsm_metadata.sh` (one test translation unit,
not a rebuild of the solver). It passed 17 checks, including 2,000 enqueues from
two producer threads and snapshot reads from a third thread.

- Real `Fsm::enqueueGoal` increments the queued revision, retains a pending
  latest-only goal, and sets the existing started flag.
- Real `getGoalDemandSnapshot` reports a consumed-but-still-processing goal as
  pending through the production `GoalUpdateScope` lifetime.
- Production scope destruction clears processing state for rejected and
  exception-unwound processing, without falsely incrementing acceptance.
- Acceptance increments once and does not erase a newer callback's pending goal
  queued concurrently during processing outside the queue mutex.
- Synchronized getters retain monotonic queue revisions and count all 2,000
  concurrent enqueues. This is a deterministic behavioral check, not a TSAN
  proof of absence of every possible race.
- Real `tryConsumePendingGoal` returns false for an empty queue.
- Real `callReplanOnce` returns empty own-commit metadata for each of its four
  early gates: stop, not FOLLOW_TRAJ, finished and plan-from-rest. The latter
  retains its existing reset behavior.

Only the consume handoff itself is arranged by the probe under the actual
protected mutex. It does not invoke map readiness, nearest-cell goal adjustment
or the rest of `tryConsumePendingGoal` with a fake planner and claim that this is
a full callback integration test. Its virtual publishers are no-op stubs.

## Pure policy tests

The production pure helper and prototype counterpart pass 41 individual gate
cases, 21 nonfinite cases, backup/receipt endpoint cases, and a simulated 100 Hz
guard/command versus 15 Hz demand schedule (5 solves, 10 skips in the example).
The prototype also passes ASan/UBSan. This demonstrates decision logic given
truthful coherent evidence, not actual ROS executor cadence or CPU savings.

## Reviewed/built, not dynamically exercised by these fixtures

- Actual successful ReplanOnce own-commit output attribution under the planner
  lock, concurrent PlanFromRest behavior, and no-commit SUCCESS/NO_NEED paths.
- The new strict receipt renewal's getState failure and mixed-map rejection.
  The pure test rejects an invalid/mismatched receipt, but does not inject those
  failures into the actual trajectory/map implementation.
- Event request arrival while the real 100 Hz handler is executing. Review
  verifies a separate atomic completion update after handling, but the metadata
  test does not instantiate FsmRos2 or mock a brake activation.
- Root's end-to-end package build covers the ROS2 API/atomic/formatter changes.
  ROS1 call sites were source-checked for ignored return values/default planner
  outputs; a ROS1 build is not available or claimed.

Matched closed-loop flights, fresh certificate/receipt eligibility, unchanged
command/odometry/recovery cadence, safety, runtime quality and CPU reduction
remain separate evidence; none follows merely from these unit/preflight passes.
