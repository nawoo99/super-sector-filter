# Demand certificate refresh: read-only source review

Status: proposal only, 2026-09-16. No runtime edits, build, or flight by this
review. Implement only if C12's final-reason histogram supports the opportunity.

## Exact current path

- `super_planner/include/ros_interface/ros2/fsm_ros2.hpp:3720`,
  `collectDemandEvidence()`: captures simulation time first, then committed
  shared trajectory, map health, and the mutex-protected `safety_certificate_`.
  It does not validate geometry itself.
- `fsm_ros2.hpp:3810`, `tryDeferOrdinaryReplan()`: calls the pure decision policy;
  only `NEED_VIABILITY_RENEWAL` invokes additional work. That work is
  `SuperPlanner::renewCommittedStopViability()`, followed by complete evidence
  recollection. Neither stale-certificate nor geometry reasons get a refresh.
- `fsm_ros2.hpp:3891` vicinity, `replanTimerCallback()`: a failed deferral falls
  through to the existing ordinary `callReplanOnce()`. Existing prechecks may
  already return before demand evaluation when revalidation is pending or the
  map is too old. Histogram counts are therefore not all 15 Hz timer ticks.
- `fsm_ros2.hpp:2152`, `refreshSafetyCertificate()`: reused by main_pre/main_post
  in the 100 Hz main callback, poly publication, replan_post and brake recovery.
  It caches by map/generation; otherwise calls `validateCommittedTrajectory()`.
  It writes shared certificate state and clears `safety_revalidation_requested_`.
  Do not casually add a new concurrent caller for a skip-only optimization.
- `super_planner/src/super_core/super_planner.cpp:677`,
  `validateCommittedTrajectory(now)`: captures the committed trajectory,
  validates its remaining geometry, and rejects a changed generation.
- `super_planner.cpp:242` vicinity, `validatePositionTrajectory()`: records
  `checked_from_tt` and `checked_to_tt = total_duration` (line 269), queries
  under a map read transaction, then rejects changed map identity. Normal
  committed validation permits the existing escape handling; a skip receipt
  must additionally reject both escape/egress flags, just like today's policy.

## Meaning of the two suspected reasons

`demand_replan_policy.hpp:185` vicinity: `STALE_OR_UNCERTIFIED_MAP` combines a
motion-stale map, absent/non-SAFE certificate, zero map version, certificate
generation mismatch and certificate map mismatch. A new immutable-map commit
can make an otherwise safe same-generation certificate obsolete before the
next main guard refresh. During that interval, demand can fall through to an
ordinary solve instead of doing a geometry check. This is a plausible source
opportunity, not a measured C12 attribution yet.

Current trajectory generation must still equal the last successful *own*
ordinary commit. `NO_SUCCESSFUL_LEASE` is checked before the map reason. A
foreign/new generation must never be repaired by refreshing geometry or by
relabeling the old lease. The narrow candidate below only handles a previously
explicit-SAFE certificate for the same leased generation and an older map.

`demand_replan_policy.hpp:220`: `INSUFFICIENT_GEOMETRY` means a nonfinite bound,
certificate start later than the captured current time, or certificate end
shorter than the required horizon. It is **not normally an expiring short
geometry horizon**: current SAFE geometry covers the trajectory to its end.
If `required_until_tt > total_duration`, another validation cannot create more
trajectory and must not permit skipping. Backup/moving-horizon limits are also
unchanged. The certificate-start inequality can instead be a collection race:
the collector captures now before another callback publishes a later-starting
certificate. One fresh recollection can resolve that race without relaxing
the inequality or sleeping. A true clock anomaly must remain disqualifying.

## Narrow candidate, after histogram confirmation

1. Recollect once, without waiting, when metadata suggests a concurrent cache
   update. Re-run the identical decision; do not change thresholds.
2. Consider one local geometry refresh only for the old-map/same-generation
   SAFE-certificate case. Require immutable snapshots, fresh motion map,
   matching successful own-commit lease, valid clocks, clean goal/event/recovery
   and safety state, sufficient moving trajectory, and an unexpired dispatch
   deadline. Do not run it just because the broad reason label was returned.
3. Call the existing committed validator once using the current simulation
   time. Require explicit `SAFE`, no clearance escape or initial-footprint
   egress, and the exact expected current generation and map version.
4. Keep its result as a callback-local receipt, not a replacement shared guard
   certificate. Recollect all evidence and both clocks; use the receipt only
   if identities and coverage still match. Prefer an already-current shared
   SAFE certificate. Never override an explicit unsafe certificate for the
   current generation/current map. A changed generation/map invalidates this
   attempt rather than causing an unbounded retry.
5. Require the unchanged current-map sampled stop-viability receipt. If needed,
   perform the existing bounded renewal, recollect again, and apply the same
   final policy. The geometry receipt must survive these identity checks too.
   Renewal policy revision, sample spacing and existing stop acceptance remain
   unchanged; this is not a stricter runtime emergency-brake proof.
6. Any failure follows the existing non-deferral path. No sleeping, waiting for
   a future observation, lease extension, pending-event consumption, or blind
   skip is introduced. Expiration during validation is checked with fresh
   time, not the pre-validation timestamp.

## Forbidden state changes

The skip-only path must not write `safety_certificate_`,
`safety_certificate_valid_`, `safety_revalidation_requested_`, recovery/brake
flags, goal revisions, event completed counters, Full-refresh gates/ACKs,
committed trajectories, `demand_success_generation_`, or
`demand_success_dispatch_`. In particular it must not call the mutating
`refreshSafetyCertificate()` helper merely to manufacture skip eligibility.

## Evidence and bounded tests

C11 profile offers motivation only: Full geometry averaged about 0.0435 ms per
call over 3,258 calls, versus EXP optimization 10.414 ms and BACK optimization
4.869 ms per call. These are mixed-call means, not a predicted geometry-refresh
cost or guaranteed saving. C12 must first show enough relevant final reasons.
The aggregate reason alone cannot distinguish real stale sensing from cache
lag; optional callback-owned subreason counters would make this explicit.

Required tests before any flight:

- Same leased generation / old SAFE map -> new explicit SAFE receipt may
  continue to the unchanged viability and final checks.
- Foreign generation, expired lease, actual stale map, pending goal/event,
  current unsafe result, escape/egress, invalid clocks and insufficient moving
  duration must never become eligible through this refresh.
- Map/gen changes during validation, viability renewal, or final recollection
  reject the local receipt. No shared safety flags are cleared.
- Concurrent newer certificate start can recover only through a fresh now;
  NaN bounds and actual insufficient trajectory duration remain rejected.
- Validation time that crosses dispatch/coverage/freshness limits fails closed.
- Counters distinguish refresh attempts, explicit-safe results, reuse after
  recollection, failed identities and actual additional skips; compare common
  Full/Adaptive CPU, path/time quality and the existing source/recovery audit.

No additional sensing/control throttle, weaker geometry test, or relaxed
coverage/backup/stop condition is proposed.

## C12 measured decision: defer this optimization

Run9313 completed with the extended .5s dispatch cap. The final available 5s
histogram reports contain 528 Full and 514 Adaptive demand decisions (not the
unreported tail or timer ticks gated before demand):

| Reason | Full | Adaptive |
| --- | ---: | ---: |
| SKIP | 379 | 360 |
| STALE_OR_UNCERTIFIED_MAP | 10 | 12 |
| INSUFFICIENT_GEOMETRY | 0 | 0 |
| DISPATCH_DEADLINE | 31 | 26 |
| INSUFFICIENT_MOTION_HORIZON | 28 | 23 |
| NEW_GOAL | 43 | 38 |
| VIABILITY_RENEWAL_REJECTED | 15 | 22 |

Stale/uncertified represents only 1.89% / 2.33% of these decisions, and the label
still includes non-refreshable conditions. Certificate refresh is therefore
low priority, not a justified major CPU optimization now. Parent directed no
implementation. Preserve the proposal if later profiles show a different
bottleneck; do not relax the more common deadline/horizon/goal/stop gates.
