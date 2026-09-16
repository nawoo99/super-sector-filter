# Reviewable prototype status

Both final proposals have now been applied to runtime with `apply_patch`, after
root and independent reviewer approval. Root owns the full workspace build and
matched flight validation. The runtime remains default-off for this feature.

Applied order:

1. `01_evidence_api_proposal.patch`
2. `02_fsm_hookup_proposal.patch`

Both together passed `git apply --check` before application; the applied runtime
passes `git diff --check`. These check contexts/whitespace, not runtime safety.
The complete pre-application staged source remains under `patch_stage.W86rGS/`
as a review artifact; the real code is now in the runtime workspace.

## Scope

- New pure helper defaults off; enable proposed runtime via
  `SUPER_GUARDED_DEMAND_REPLAN=1` in BOTH matched Full/Adaptive modes.
- 0.25 s nominal dispatch cap; unchanged 15 Hz demand, 100 Hz guard and command
  timers; no sensor cadence/resolution/FOV change or data outside Sector.
- Skip-only strict stop-viability renewal reads the current shared command
  snapshot. It does not modify existing candidate acceptance or rescale a path.
- Every requested state must be evaluated, the full renewal loop must keep the
  same map version/current generation, and updated clocks/sample/evidence are
  recollected after renewal. At most one renewal per demand check.
- Sampled current-policy caveat remains explicit: unknown=false and acceptance
  of CLEARANCE_MARGIN are inherited, not a continuous runtime-brake guarantee.
- Legacy weaker same-map coalescing is bypassed while the new feature is enabled,
  so a failed new-policy gate cannot accidentally fall through to a weaker skip.

## Attribution and race protections

- Optional `ReplanOnce` outputs report its OWN committed generation and steady
  commit timestamp while its existing planner lock is still held. Failure,
  hold and SUCCESS/NO_NEED without a commit leave outputs empty. This avoids
  misattributing a concurrent PlanFromRest commit to an ordinary moving solve.
- A small Fsm moving outcome carries those values. Existing ROS1/manual call
  sites ignore the return value; three-argument planner callers keep defaults.
- Goal queued/update-in-progress/accepted revisions use the existing pending
  goal mutex. An RAII scope covers all returns from consumed-goal processing.
- New non-consuming views expose rejection/topology demand without stealing it
  from the existing safety handlers.
- Event-request completion is separately published atomically AFTER main-FSM
  handling. A newly requested but not yet handled event blocks skips, including
  the old handled-before-brake-activation window.
- Final evidence checks repeat generation/map/goal/event/FSM/stop/finish/
  PlanFromRest/brake/revalidation/recovery-announcement conditions.
- A backward/nonfinite simulator clock invalidates the skip lease and receipt,
  even if the old receipt's TT range would still contain the new clock value.
- Dispatch-to-own-commit duration must fit the configured 0.1 s engineering
  budget to earn a lease. The old overtime check excludes commit work, so it is
  not used as an end-to-end timing guarantee. Scheduler stalls remain possible.

## Evidence completed

- Pure helper optimized tests pass: 41 individual gate cases, 21 nonfinite
  cases, endpoint/deadline checks, and fake 100 Hz cadence preservation.
- Final 41-case revision also passes ASan/UBSan, recorded in
  `prototype/observed_output.txt`.
- Both final patch files passed combined dry-run context checking and independent
  review; applied runtime whitespace checking passes.
- Root completed the affected ROS2 package build successfully before the
  actual-Fsm test compile. Actual-Fsm metadata integration tests then passed:
  17 checks, 2,000 concurrent enqueues and four real early-replan outcomes.
  See `fsm_metadata_observed_output.txt` and `INTEGRATION_TEST_COVERAGE.md`.
- No ROS1 compile, full callback/solver integration fixture, matched flight, or
  real-CPU reduction measurement is claimed yet in this file.

## Remaining blockers before flight

1. Root and independent reviewer approval/application: completed.
2. Affected ROS2 consumers built successfully (including shared API signature
   changes). Source searches found ROS1 `callReplanOnce()` ignores the returned
   value, which is compatible; no ROS1 build is claimed.
3. Add or run integration-focused tests for strict renewal failure/mixed-map
   rejection, goal enqueue/consume gap, event-before-handler gap, own-commit
   attribution, failed/NO_NEED lease rejection and dispatch-overrun rejection.
   The pure decision test cannot establish callback synchronization by itself.
4. Add runner flag/startup-marker validation, same policy in both modes, then
   freeze and run matched seed1 n=1 with command/odom/ACK/recovery audits.

The policy can reduce ordinary solver calls but may have low eligibility under
strict gates. Neither a 40% reduction nor preserved flight quality is established.
