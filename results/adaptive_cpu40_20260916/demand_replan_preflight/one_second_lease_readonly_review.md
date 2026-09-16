# Optional 1.0 s dispatch cap: read-only review after C14

Status: proposal only. No runtime/config/runner edit, compilation, or experiment
was performed for this review while the C15 build was running.

## Recommendation

A separately opted-in 1.0 s dispatch-age cap is defensible as a **bounded
simulation ablation of the existing sampled policy**, provided every current
per-tick gate and the 15 Hz demand / 100 Hz guard-command timers stay unchanged.
It is not a one-second blind wait, a stronger emergency-stop guarantee, or a
progress guarantee. I do **not** recommend it as the primary next route to the
40% CPU target: C14 leaves too little measured replanning CPU for this parameter
alone to supply that gain. Default 0.25 s and the current explicit 0.5 s option
must remain unchanged; current code correctly rejects 1.0 s as INVALID_POLICY.

## Actual dependencies in current code

- `super_planner/include/super_core/demand_replan_policy.hpp::decide` uses the
  maximum cap only for configuration validation and
  `last_successful_dispatch_steady_s + max_dispatch_interval_s`. It dispatches
  whenever the next demand tick plus scheduling reserve would pass that deadline.
  None of the safety-horizon equations derives its horizon from 0.5 s.
- The required rolling interval remains current trajectory time + demand period
  + scheduling reserve + configured solve budget + command handoff reserve:
  currently approximately `0.066 + 0.02 + 0.10 + 0.02 = 0.206 s` ahead. Longer
  dispatch age must NOT extend an old receipt or bypass this rolling test.
- `fsm_ros2.hpp::collectDemandEvidence` re-reads map freshness, explicit SAFE
  certificate, exact current map/generation, goal revisions, ordinary state,
  brake/revalidation, recovery/Full-refresh/event demand, failed/rejected/topology
  state, current trajectory time, backup state, and final-coherence checks.
  `tryDeferOrdinaryReplan` does that every demand callback and recollects evidence
  and current clocks after any receipt renewal. The legacy weaker coalescer stays
  bypassed. Map updates do not extend the successful-dispatch timestamp.
- `super_planner.cpp::renewCommittedStopViability` requires immutable publication,
  same expected generation/version before and after, finite states and successful
  checks for every requested discrete sample through the configured horizon
  (currently 2 s, clipped by trajectory duration). A failed getState/stop test or
  intervening publication invalidates the receipt. No stale cross-map reuse.
- `decide` still dispatches before an appended/carried backup or trajectory tail
  intrudes into the rolling required interval. A .7 s motion segment therefore
  cannot use a 1.0 s lease to run into its backup; motion-horizon dispatch wins.
- `recordDemandReplanOutcome` alone renews the lease after an own successful
  ordinary commit, with unchanged goal/event metadata and measured
  dispatch-to-commit within configured forward time. Skips, duplicate commands,
  failed solves, unrelated PlanFromRest commits and viability renewals do not
  renew it. An over-budget solve cannot mint a replacement lease.
- This remains the existing sampled stop policy: unknown space is allowed by
  that check and CLEARANCE_MARGIN can pass. Its receipt is NOT equivalent to the
  stricter runtime emergency-brake certificate. Configured 0.10 s solve time is
  an engineering budget, not a guaranteed scheduler/solver upper bound.

Thus a 1.0 s option does not logically require weakening those predicates. It
does change which valid-but-aging trajectory is selected to continue, and hence
which future optimizer inputs/paths occur. It is not behavior equivalence.

## Quality and liveness risks that certificates do not detect

`fsm.cpp::callReplanOnce` remaps the **current effective** `gi_.goal_p` to a nearby
unoccupied inflated cell before each actual solve. Goal revision equality only
means the command did not change; it does not certify that this effective target
or route is still optimal after a map update. Coalesced retransmissions likewise
do not reproject the original raw goal. A 1.0 s cap can defer another .5 s of
effective-target remapping, route shortening or new-route selection even while
the current trajectory remains geometrically SAFE. At 7 m/s, .5 s is as much as
3.5 m of additional travel along that existing trajectory.

The policy has no explicit actual-odometry progress/stagnation or path-regret
gate; an unfinished desired command sample is not proof of achieved progress.
Existing main-FSM/command completion and guard recovery continue, and the finite
dispatch-age cap supplies eventual *attempts* under the assumed executor cadence,
not guaranteed route discovery or finite mission completion. Backup/horizon gates
may trigger well before the cap. Larger caps could cause additional braking,
poorer turn anticipation or longer mission time despite contact-free results.

## Measured gain ceiling: useful but not a performance guarantee

Source: C14 `thread_cpu_summary.json`, final paired summary, and last periodic
reason histograms. The profiler windows are 30.0587 s Full / 35.0686 s Adaptive,
not exactly the whole-flight cgroup windows; projections below are indicative.

| C14 observation | Full | Adaptive |
|---|---:|---:|
| Whole-experiment mean cores | 0.579354 | 0.423070 |
| Inclusive replan-core CPU / profiler window (s) | 2.325449 | 2.993366 |
| Inclusive replan-core mean cores | 0.077364 | 0.085357 |
| Mean inclusive CPU per replan-core call (ms) | 22.799 | 24.739 |
| Last-report DISPATCH_DEADLINE outcomes | 43 | 42 |
| Last-report INSUFFICIENT_MOTION_HORIZON outcomes | 23 | 24 |

The reason histogram checks deadline **before** geometry/motion/receipt gates.
A deadline count therefore does not mean the callback would otherwise safely
skip. Extending the deadline may reveal a different dispatch reason, not remove
the solve. Counts are last periodic reports, not final whole-flight totals.

If every current deadline solve cost the overall mean, deleting all 43/42 would
save only about .980/1.039 core-s; deleting half projects around .0131 mean core
per mode. These are coarse hypothetical estimates, not observed speedups.

Even deleting **all** measured replan-core work, while holding the remaining
workload unchanged, projects only
`1 - (0.423070-.085357)/(0.579354-.077364) = 32.73%` relative reduction. Achieving
40% by removing the same common cost from both modes would require about .18864
core per mode—more than twice this entire replan stage. This is a stationary
workload ceiling for the identified CPU component, not a rigorous upper bound on
new closed-loop paths, frequencies, cache behavior or another optimization.

## Required validation if root chooses an ablation later

1. Exact independent opt-in; main policy disabled cannot enable the extension.
   Preserve old .25/.5 parsing, reject malformed values and caps above 1.0, audit
   the selected cap in both-mode startup and histogram/runner metadata.
2. Parameterize all current pure-policy rejection tests at .25/.5/1.0. Check
   deadline exactly at and one ULP around the boundary, and show .206 s required
   horizon is identical across caps. A one-ULP-short certificate/receipt, changed
   map/gen, expired lease, failed state lookup, backup/tail boundary and any
   goal/recovery/failure event must still dispatch or refuse the receipt.
3. Simulate advancing trajectory time beyond the original .5 s, several new map
   versions and receipt renewals; ensure each skip needs renewed current evidence
   and no renewal/duplicate command changes dispatch age. Clock rollback and a
   long renewal must invalidate/recompute the evidence as today. Exercise short
   motion horizons that force dispatch before the new maximum.
4. Preserve actual-Fsm metadata/identity regressions. Source-check no timer change,
   no earlier returns outside the existing demand hook, no new stale-cache reuse,
   and no expansion of sampled-stop acceptance. Pure synthetic tick tests are not
   proof of real executor cadence.
5. Matched Full/Adaptive seed1 run with all other settings identical; retain
   contacts=0, completion, speed, 100 Hz command/odom, all paired and per-mode time
   gates. Audit positive cap-limited skipping in both modes, changed deadline vs
   motion/renewal reason counts, and guard/brake/Full recovery frequency. Reject
   if CPU improvement comes from longer waiting or worse mission performance.
   Explicitly test/map-observe target remapping/turn response before broader use.

There is no source-level necessity to try this cap before C15's bounded common
runtime/static-delivery work. Any result still needs unprofiled confirmation and
later multi-map regression; C14 n=1 does not justify adoption by itself.
