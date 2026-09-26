# Stopped departure clock contract: design only

Date: 2026-09-26. No implementation authorization or planner-core edit is
implied. This proposal covers both ordinary and certified emergency from-rest
departures; the current v3 ordinary gate alone does not cover both.

Post-smoke clarification: G1 Full also demonstrates a separate spatial start
mismatch. The grid-centre selector feeds a snapped position into fresh EXP
initial PVA rather than the physical held point; at the observed origin the
minimum offset is 43.301 mm. The staged API therefore must preserve the exact
physical held PVA and treat the snapped point only as a search seed, with a
validated corridor/connector. Rebase alone cannot fix this. See the finalized
`g1_full_handoff_cause_audit.md` for source chain and measurements.

## Why an outgoing timestamp edit is insufficient

`generateExpTraj` assigns `new_traj_WT = replan_process_start_WT`, then stores that
clock in the EXP position/yaw trajectories. `PlanFromRest` can spend time in path
search, corridor generation, optimization and validation before it returns.
`commitTrajectoryCandidate` starts its validation at current time minus that
start time. This is not proof that a previously held command can jump to the
candidate's current PVA or that the skipped prefix was validated for departure.

Changing just `PolynomialTrajectory.start_wt` would disagree with CmdTraj's
immutable snapshot, command samples, future EXP reuse, backup phase membership,
initial-footprint receipt and safety certificate. Retiming only the published
message is therefore unsafe. The existing emergency finalizer has the same
solve-start-clock exposure, even though it has separate brake/map/ACK checks.

## Recommended architecture, if separately approved

Use one planner-owned **staged stopped candidate** API for both finalizers,
rather than mutating the live committed path from the FSM. Keep shape in
trajectory-relative time until an explicit main-side release transaction.

1. The worker returns an immutable staged object containing position/yaw shape,
   backup/carry relative boundaries, its matching EXP cache, exact request,
   pre-solve generation, held PVA/yaw, and stop/goal/map identities. Shape
   construction and geometry/viability checks remain on the worker. No
   executable-generation advance should occur before acceptance.
2. Validate the entire prospective departure prefix beginning at `tt=0`, not
   `now-solve_start`, using the same bounded guard/stop policy. Validate against
   an immutable map version. A new map version requires revalidation or safe
   rejection; translating timestamps cannot renew an old proof.
3. Immediately before release, main checks exact pending request, hold/brake
   revision, current generation, goal/stop/event/ACK identities, map freshness,
   finite stationary odometry and shape PVA at `tt=0` against the held sample.
   This uses the same position/velocity/acceleration thresholds, not a larger
   continuity allowance.
4. A planner-owned bounded commit transaction assigns one release clock and
   atomically installs **all** matching clock-bearing state, advances generation
   once, and yields the exact shared snapshot plus a generation-bound current
   certificate. Main publishes that snapshot while command publication remains
   quarantined under the safety lock. Both ordinary and brake-release callers
   use the same contract. Rejection leaves the old hold/brake executable.
5. PositionCommand publication at the actual first tick and the polynomial
   consumer need a common start convention. Releasing at an earlier preparation
   time merely recreates the flaw. A small clock transaction must sample at
   actual release, or a formally defined future-start stationary prefix must
   be supported by **all** consumers. The latter is not presently implemented
   and is not permission to raise budgets or accept an arbitrary jump.

## State that must agree in that transaction

- CmdTraj position and yaw `start_WT`, its `start_WT_`, immutable snapshot,
  generation and any commanded sample identity.
- `last_exp_traj_info_`: both position/yaw clocks and its internal start field,
  or explicit cache invalidation until a matching staged EXP is installed.
  Preserve matching SFC/known-free/connected-goal metadata; do not reuse an
  older unscaled or differently clocked EXP on `NO_NEED`.
- Appended/carry backup boundaries stay relative to the exact same shape;
  any stored backup absolute clocks and planner on-backup tracking must be
  updated consistently or invalidated. Do not translate relative times twice.
- `guard_rest_to_rest_hold_until_wt_` must refer to the new release clock and
  the proven staged terminal/hold duration, not the old solve-start instant.
- Safety certificates bind the new generation, exact map version, policy and
  checked relative interval, including the departure prefix.
- Initial-footprint egress is particularly delicate: the existing receipt
  binds generation, start clock, origin, exact hit set and bounded relative
  permission. Do **not** just move its deadline forward. Re-prove a fresh
  staged departure against the same actual stationary footprint, or reject
  such a staged candidate for the first implementation. Any fresh proof must
  retain no expanding hit mask and an explicitly bounded permission interval.
- Planner log/visualization timestamps may be diagnostic-only, but must not
  accidentally overwrite executable clock state or imply old certificates
  cover newly exposed prefix samples.

## Bounded API sketch

Conceptual types, not implemented interfaces:

```text
prepareFromRest(request, pinned_hold, immutable_map) -> StagedCandidate
validateStoppedDeparture(stage, immutable_map) -> RelativeCertificate
commitStoppedDeparture(stage, certificate, expected_identity, release_wt)
    -> AcceptedSnapshot OR reasoned rejection
```

Preparation owns the matching EXP/cache metadata; commit must perform no A*,
corridor construction or trajectory optimization on the 100 Hz thread. Large
copies or allocations can be prepared before the transaction and installed
by shared ownership. Main must not block waiting for a worker-held solver lock.
If map/generation changes before installation, reject/requeue rather than
doing unbounded revalidation in the publication lock.

## Required tests before enabling

- Identical held pose, varying solve duration: first accepted sample is the
  same departure PVA and no prefix silently disappears.
- Goal/stop/brake replacement and exact ACK change at each stage: no release,
  no generation exposure, hold remains published.
- Worker completion races command publication: neither old hold after new
  path nor staged path before its release transaction is observable.
- Full map-version change between worker validation and commit rejects stale
  evidence; same immutable map admits the matching generation only.
- Position/yaw/CmdTraj/EXP clocks agree after commit; subsequent `NO_NEED`,
  ordinary replan, appended backup and emergency sampling use the same clock.
- Occupied/unknown/invalid state in the previously skipped initial prefix
  fails the unchanged relevant policy. Egress receipts cannot expand or renew
  accidentally during retries.
- Rest-to-rest hold deadline and backup relative boundaries remain correct
  under clock translation; generation changes exactly once.
- Both ordinary and certified emergency release execute the shared policy;
  an ordinary rejection must not bypass continuity through emergency recovery.

This staged API is more than a one-line timestamp correction. It should be a
separate revision with archived source/binary identity and prospective smoke,
not an unrecorded mutation during the current build or flight.
