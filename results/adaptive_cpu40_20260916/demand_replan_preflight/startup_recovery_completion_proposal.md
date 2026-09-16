# C7 startup-recovery announcement lifecycle defect and bounded repair

Status: reviewed and applied for C9. The production binding is in
`super_planner/include/ros_interface/ros2/fsm_ros2.hpp`, with the shared pure
helper under `include/fsm/startup_recovery_completion_policy.hpp`. Root owns the
final build, mirror and matched flight. This document preserves the reviewed
design and its limits; test passes alone do not establish flight eligibility.

## Observed defect

`seed1_run9308_full.attempt1.stack.log` line 457 announces recovery active after
the initial PlanFromRest EXP clearance rejection. Brake construction immediately
returns because no usable odometry-derived state, cached command or current
trajectory sample exists. The next ordinary PlanFromRest succeeds, but the
announcement never becomes false: only successful active-brake recovery clears
it. Every new demand lease is consequently rejected. The logged NEW_GOAL is a
secondary effect of its never-populated successful-goal metadata, not repeated
goal callbacks. Full had zero skips/renewals; Adaptive exercised the policy.

C7's measured relative CPU result is therefore not a fair adoption result.

## Scope

Repair only the observed **pre-first-committed-trajectory** episode. Do not remove
the demand policy's recovery exclusion, clear on a bare FOLLOW_TRAJ state, clear
after timeout, or release an active brake. Default guard/command/viability policy
does not change. The lifecycle repair is shared by Full and Adaptive, with the
existing extra Full observation/ACK requirement when a frontend is present.
The new completion supports only the event-recovery frontend, whose ACK handler
requires `committed=1`, or a genuine no-frontend case. An advertised legacy
non-event frontend has no committed bit in its existing ACK cache; it receives
no new completion path and no new planning hold from this helper.

The narrow episode may be armed only at the `getOneCommandSample` failure in
`activateEmergencyBrake`, with all of:

- current committed generation zero AND shared command snapshot empty;
- no previously published cached command;
- no active brake, not FOLLOW_TRAJ or EMER_STOP;
- state INIT, WAIT_GOAL or GENERATE_TRAJ, and no successful brake constructed.

Every activation attempt has a new monotonic revision. Its entry invalidates
older startup eligibility; the exact failure above can arm the new revision.
Any constructed brake or incompatible failed attempt leaves it unarmed.

## Serialization and publication

1. Move `publishTrajectoryGuardRecoveryState(true)` inside the existing
   `brake_activation_mutex_`, immediately after taking that lock and advancing
   the attempt revision. Currently publication precedes that lock, permitting
   completion to erase a newer waiting activation edge.
2. Do not hold that mutex across ordinary PlanFromRest. Capture a small proof
   before the call; completion reacquires the mutex and demands the same armed
   revision. A newer attempt wins and invalidates the old proof.
   If its try-lock is busy, defer only GENERATE_TRAJ with an empty generation-zero
   snapshot for one tick. A competing activator may not have published true or
   armed the ACK gate yet; do not read its protected state or start the first
   path through that gap. Existing nonzero trajectories retain their behavior.
3. The final false edge is not mere metadata: it can close Adaptive to Sector.
   It must atomically consume the matching Full-ACK gate, not clear an unrelated
   newer request. Use one `full_refresh_mutex_` transaction to recheck exact
   target sequence/stamp/ACK map + latest request/ACK and consume that gate.
   Factor `clearFullRefreshRecoveryGateLocked()` for use inside this transaction;
   do not call an existing helper that re-locks the mutex while it is held.
4. Serialize the event-request subscription's monotonic requested-counter update
   with the same short `full_refresh_mutex_` transaction. It currently writes
   the atomic without that mutex. A request observed before completion then
   blocks it; a later request starts a new ordinary episode after the false edge.
   Do not take this mutex across a solve or brake search.

Lock order for completion: activation mutex; gather/validate current certificate
under a short safety-mutex scope and release it; then Full-refresh mutex for final
token/event/episode verification and false publication. Avoid safety/full mutex
nesting. New map/generation changes still fail through the existing 100 Hz command
and guard checks; this does not claim an atomic transaction with the entire map.

## Before ordinary initial PlanFromRest

At main-FSM entry immediately before `callMainFsmOnce`, if an armed startup episode
exists and the state is GENERATE_TRAJ with generation zero:

- Continue existing map-readiness/odometry checks.
- With an event frontend or advertised Full-refresh gate, require a nonzero
  selected target, target >= required minimum, exact ACK, a committed ACK map
  newer than the episode boundary, and no unacknowledged newer latest request.
  The Full-only case with no event frontend and no advertised gate has no
  external ACK to wait for.
- A missing Full ACK keeps the existing no-trajectory hold; do not start the
  ordinary solver yet. This establishes **ACK before planning**, not merely a
  certificate on some later map.
- Only that supported missing-ACK condition suppresses original main-FSM work.
  Other failed proof gates, especially a pending goal/topology demand that the
  original main FSM must consume, invalidate completion without blocking it.
- An already ACKed newer latest request is allowed (`latest >= selected target`)
  because the selected target freezes when ACKed. Requiring equality would
  deadlock after a valid retry scan. A newer unACKed request still blocks.
- Capture the armed activation revision, goal revisions, event requested and
  completed revisions, initial generation zero, and exact ACK identity/map.
  No pending/in-progress goal is eligible for completion proof. A goal race is
  fail-closed for this narrow repair, not permission to close sensing.
- The known corridor/topology retry flag from the first rejection is allowed
  before planning, because PlanFromRest resolves it. Final completion requires
  it and any candidate rejection to be clear. The expected one-shot
  `plan_from_rest_` flag after success is not a reason to reject completion.

## After the call

Require actual transition from GENERATE_TRAJ with generation zero to FOLLOW_TRAJ
with a positive current generation, and obtain the existing main_post certificate.
Since no command trajectory existed before this callback, a positive generation
requires a successful PlanFromRest before any concurrent moving replan can occur.
We do not infer ownership of a particular later generation from a before/after
comparison; the final certificate/sample refers to the actual current one.

Under the serialization above, require all of:

- same armed activation revision, recovery announcement still true;
- unchanged accepted/queued goal identity, no pending/in-progress goal;
- event request unchanged and completed; no pending event;
- no active brake, EMER_STOP, stop/finish, revalidation, candidate rejection or
  topology retry demand;
- explicit SAFE certificate (not `safe()`'s aliases), exact current generation
  and current immutable map version, fresh map, sufficient checked range;
- `getOneCommandSample(sample, current_generation)` succeeds, is finite and not
  finished/on backup, with matching start/time range;
- exact same post-event Full ACK target/map and no new unacknowledged request,
  with certificate map >= ACK map; no-frontend Full remains the explicit case;
- final current generation/map, goal/event and activation revision unchanged.

For Adaptive emit the ordinary `[EVENT_RECOVERY_PATH_READY]` with the actual
captured target/stamp/ACK map, generation_before=0 and current generation_after,
then publish the false recovery edge and consume only that episode's gate. Emit
a distinct `[TRAJ_GUARD_STARTUP_RECOVERED]` with revision/map/gen for both modes.
Do not alter or impersonate the actual certified active-brake completion path.

## Deliberately conservative limitation

This proposal repairs a precisely identified startup state-selection failure,
not all possible failed-brake lifecycle paths. A goal/ACK/activation race that
invalidates the captured proof leaves sensing open and solver skips disabled;
it must not be silently generalized to clear a moving recovery. Such a residual
case would be visible in the new startup-event records and require a separate
reviewed completion proof.

## Tests before adoption

The adjacent pure helper/test fixture exercises the complete eligibility facts,
revision loss-of-edge race, empty-to-new-path ordering, exact ACK-before-plan,
newer request/goal/activation rejection, SAFE/finite/sample rejection, and the
two valid Full/no-frontend and Adaptive/post-ACK cases. It does not prove ROS
lock ordering or a true planner callback; those require concrete patch review
and matched C9 flight logs. Both modes must actually exercise demand skipping
before the corrected relative CPU measurement is interpreted.

Final production pure fixture: 104 checks PASS in optimized and ASan/UBSan
builds. Root deliberately interrupted build session 57407 with SIGINT to apply
the reviewed contention fix before consumers compiled the final header; that
interruption is not reported as a compilation error. Final build/flight results
belong to the root campaign artifacts.
