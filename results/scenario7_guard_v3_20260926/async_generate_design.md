# Ordinary GENERATE_TRAJ dispatch: pre-implementation design

Historical design snapshot. Implementation/offline-validation status is now in
`async_generate_validation.md`; the coordinated follow-up clock-contract design
is in `stopped_clock_rebase_design.md`. The hold notes below describe this
document's original preimplementation stage, not the current build status.

Date: 2026-09-26. Status: architecture approved by coordinator; existing
production edits remain on hold until unchanged-v2 Urban probe terminates.
No claim of implementation completion or flight validation is made here.

## Problem and scope

`Fsm::callMainFsmOnce()` executes `PlanFromRest` synchronously in GENERATE_TRAJ.
That work includes path search, corridor construction, optimization and guards;
it runs on the mutually-exclusive 100 Hz main callback. Certified emergency
recovery already uses a bounded single-flight reservation on the existing
replan executor, but ordinary GENERATE_TRAJ does not.

Introduce a separate, exact opt-in `SUPER_ASYNC_GENERATE_TRAJ=1`, default off.
Do not change A* work budgets, geometry/radius, margin thresholds, timing gates,
or sensing policy. In particular, ordinary generation must not automatically
open Full sensing merely to reuse emergency-recovery code.

## Ownership and lifecycle

1. Add a virtual base-FSM dispatch hook immediately before ordinary synchronous
   `PlanFromRest`. Default false preserves legacy/ROS1 execution. The ROS2
   implementation submits one immutable request and returns without solving.
2. Main owns goal admission and captures queued/accepted goal revisions, exact
   raw goal creation identity, hold reservation revision, prior/current
   trajectory generation, brake revision, event epochs and any actually armed
   Full-frame/map ACK. A non-armed ordinary request has a canonical no-ACK
   identity; event-recovery configuration alone must not invent an ACK demand.
3. The existing mutually-exclusive replan callback performs computation inside
   existing CPU/timing scopes. It alone refreshes the optimizer's mutable robot
   state, calls `PlanFromRest`, consumes its rejection flag and records its log.
   No detached thread, growing queue or concurrent solver is introduced.
4. Main retains GENERATE_TRAJ and real safety work while the reservation is
   Pending/Computing/Ready. It must not call the legacy main accessor that
   overwrites the optimizer's robot-state cache, consume the worker's rejection
   flag, or replace its not-yet-finalized receipt.
5. Main alone accepts a result after current-map certificate checks, fresh
   stationary/held-pose evidence, unchanged goal/brake/event/ACK identity,
   generation advance and a valid unexpired command sample. The final
   publication/state transaction follows activation → refresh → safety → goal
   lock order. No lock is held across optimization.
6. Goal change, stop, brake replacement, changed ACK, changed hold, map/certificate
   failure or stale generation discards the result. A reserved ordinary result
   must still be drained if an emergency starts, otherwise the recovery
   executor can deadlock behind a permanently Ready ordinary receipt.
7. Ordinary and emergency slots are admitted only by main and never jointly.
   A Ready slot reserves the replan executor until main finishes/discards it.

## Internally committed candidate quarantine

`PlanFromRest` commits internally before returning. That fact is not permission
to send commands. Pin the previously executable terminal/hold sample before
dispatch; do not reconstruct it from a new planner generation after the solve.

- Command, polynomial, and brake-fallback paths must not sample or publish an
  unreleased generation. Check the gate again under the safety publication
  mutex, not merely before constructing a command.
- Quarantine survives result discard and retry: returning the single-flight
  slot to Idle must not accidentally authorize the failed/stale committed
  candidate as a later brake's initial state.
- A valid retained terminal hold is tied to its own revision/generation and a
  current hold certificate. Initial no-path startup has no invented old
  trajectory command. If retained hold/pose validity cannot be established,
  keep movement suppressed and use the existing certified-stop path.
- Successful ordinary acceptance or successful certified emergency recovery
  releases the quarantine transactionally with publication of the exact
  accepted path; do not let a late sampled hold publish after that release.
- A GENERATE entry while the prior executable trajectory is still moving is
  not itself proof of rest. Do not turn it into an unverified stationary hold.

## Exact in-flight goal replay

A long solve can overlap the mission's 1 Hz retransmission. Revision-only
cancellation would repeatedly discard the same goal after every long solve.
The approved narrow exception recognizes only the captured **accepted raw**
request: positive creation timestamp, identical frame, and bit-exact position
and quaternion components. The currently accepted source and queued/accepted
revisions must still match; no genuinely different pending goal may exist.

Count this in a separate diagnostic. It does not mint a healthy-follow token,
change Full/recovery state, or ignore same-position requests with a new
timestamp. Once the reservation drains the exception no longer applies.
Invalid identity, new timestamp/frame/pose/orientation or changed demand uses
normal goal admission and invalidates the old result.

## Prepared additive policy fixtures

New, not yet integrated or executed at this design stage:

- `super_planner/include/fsm/async_from_rest_planning.hpp`
- `super_planner/test/async_from_rest_planning_test.cpp`

They cover identity/receipt rejection, exact ACK, valid versus stale held
publication, quarantine after discard, exact replay versus new intent, and a
two-thread single-flight compute → goal change → result → discard sequence.
Production source-contract and runtime-order coverage must be added after the
existing-file freeze is released. Policy tests alone cannot establish that all
real publication paths enforce the gate.

## Validation and limits

After source authorization: mirror corresponding files, run bounded standalone
normal/sanitized tests, request independent lock/publication review, then let
the coordinator build a separate overlay and run prospective smoke tests.
Keep v1/v2 source archives, overlays, installed binaries and results unchanged.
Actual callback rates must be measured; this change removes one source of main
blocking, not every possible long guard/odometry/map operation. It also does not
fix uncertain occupancy/unknown-space geometry or prove contact-free flight.
