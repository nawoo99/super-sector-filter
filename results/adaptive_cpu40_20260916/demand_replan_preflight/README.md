# Read-only design: guarded, bounded demand-driven moving replanning

Status: design only. No runtime, runner, configuration, build, or flight change.
Prepared during the candidate-5 source/CPU freeze. This is a possible later
common Full/Adaptive ablation, not a claimed 40% CPU result or safety theorem.

## Recommendation

Keep the 15 Hz replan timer as a demand-check cadence, and keep both 100 Hz FSM
guard and command timers unchanged. A cheap eligibility decision may suppress
only a redundant **ordinary moving solve**, never a recovery/new-goal/unsafe
trajectory response. Start with a 0.20 s nominal maximum solve-deferral window;
0.25 s is a later quality-tested setting. A failed solve must not reset the
window or earn a new skip lease.

Do not merely increase `same_map_replan_min_interval_s`: the existing coalescer
has fewer eligibility checks and cannot justify reuse across map publications.
Do not treat `replan_forward_dt` as the timer period; it is currently a 0.1 s
trajectory stitching/solver budget, and must remain unchanged in this ablation.

## Source facts

All paths below are relative to `/root/super_ws/src/SUPER`.

| Location | Current behavior relevant to the design |
|---|---|
| `super_planner/include/ros_interface/ros2/fsm_ros2.hpp:3636` | Replan callback first rejects active braking or pending revalidation/stale map, then applies optional same-map/generation/age coalescing, calls `callReplanOnce`, consumes rejection, and refreshes the geometry certificate. |
| `super_planner/src/super_core/fsm.cpp:68` | Ordinary call is gated by stop/state/finish/plan-from-rest, adjusts occupied goals, and calls `ReplanOnce`; there is no generic successful-result return to the wrapper. |
| `super_planner/src/super_core/super_planner.cpp:2520` | `ReplanOnce` runs EXP generation/optimization then backup generation/optimization and may commit. Rest-to-rest recovery has a separate hold-until early exit. `NO_NEED` backup can report success without a new committed generation. |
| `super_planner/src/super_core/super_planner.cpp:1550` | Commit checks stop viability, potentially rescales/rechecks a candidate, then commits. The bool result is not persisted as a checked interval. |
| `super_planner/src/super_core/super_planner.cpp:1774` | `candidateStopsViable` samples from clamped `checked_from_tt` through `min(total_duration, checked_from_tt + configured horizon)`; typical horizon 2 s, sample interval 0.3 s. |
| `super_planner/include/data_structure/cmd_traj.h:42` | Candidate/shared snapshot already carries generation, start, duration, appended-backup start and carried-backup interval. Shared snapshot can avoid copying polynomials. |
| `super_planner/include/ros_interface/ros2/fsm_ros2.hpp:2128` | Geometry certificate is reused only for same generation/current map and fresh motion map. Otherwise committed trajectory is validated through its remaining end. |
| `super_planner/include/ros_interface/ros2/fsm_ros2.hpp:3558` | Commands require a safe certificate, matching current map, expected trajectory generation and a second map-version check. |
| `super_planner/include/ros_interface/ros2/fsm_ros2.hpp:3830` | Main FSM retains fresh near-field/frontend hazard checks, raw-cloud safety where enabled, and geometry validation before/after normal FSM work. |
| `super_planner/src/super_core/fsm.cpp:252` | Goal subscription queues a latest-wins pending goal; main FSM consumes it later. A pending goal can exist before `gi_.new_goal` changes. |

Important naming caveat: `TrajectorySafetyResult::safe()` also accepts DISABLED.
Demand-skip eligibility must require enforcement enabled and explicit SAFE,
not a bare `safe()` call.

## Do not overstate existing stop viability

The existing bool is a **sampled, policy-specific map-checked stop-existence
test**, not a continuously certified runtime emergency-stop guarantee:

- `certifiedStopExistsFrom` passes `unknown_as_occupied=false`; the emergency
  brake path uses `unknown_as_occupied=true`.
- It explicitly accepts CLEARANCE_MARGIN as well as SAFE.
- It samples trajectory states at the configured spacing and brake dynamics at
  finite samples. Nothing proves every state between samples.
- `candidateStopsViable` currently skips a failed `getState` sample rather than
  marking an interval invalid. A new receipt must be invalid if any requested
  state was not successfully evaluated, even if the existing bool stays unchanged.
- Individual stop checks can see different map publications. A receipt must not
  combine successful checks from several publications into one map-version claim.

The proposed optimization does not relax these policies. It records their exact
scope, keeps all existing 100 Hz runtime gates, and remains simulation-validated
rather than a new safety guarantee. Strengthening brake/viability policy would
be a separate algorithm change and baseline ablation.

## Minimal new evidence/API

### 1. Per-generation viability receipt

Add an optional output to `candidateStopsViable` (or a wrapper around it) and
attach the final successful result to the **same committed generation**, not a
wall-age heuristic:

```
StopViabilityReceipt {
  valid;
  trajectory_generation;
  map_version;
  start_wt;
  checked_from_tt;
  checked_until_tt;       // actual final checked state, after time scaling
  sample_dt;
  sample_count;
  policy_revision;       // current unknown/clearance/dynamics policy identity
  every_state_evaluated;
}
```

Collect map identity/version before the whole viability loop and after it.
Only mark the receipt valid if the same publication remained current throughout,
all requested states were evaluated, and all tests passed. Each individual
validator's own map checks remain intact. A map change may invalidate just the
optional skip receipt without changing the existing commit acceptance behavior.

For a rescaled candidate, discard earlier receipts; use the final scaled
trajectory's actual checked interval. Set its generation to the value returned
by commit atomically with command metadata. Non-guard/shadow commits get invalid
receipts. Do not assume `start_wt + 2 s` is the checked end: the check starts at
an elapsed trajectory time, may be clamped to the tail, and can be rescaled.

Prefer a small metadata/shared-trajectory snapshot API rather than copying full
position and yaw polynomial arrays on every 15 Hz decision. Include the receipt
under the same CmdTraj mutex, or use a generation-keyed planner receipt mutex and
double-check generation; never independently combine fields from two commits.

### 2. Coherent ordinary-demand snapshot

Expose enough state to distinguish an ordinary straight-follow interval from
new-goal, brake, topology and sensing recovery. Do not add unsynchronized reads
of mutable `gi_`/goal fields across callback groups. Suggested atomic revisions:

- queued-goal revision increments when a goal is enqueued;
- accepted-goal revision is bound to the trajectory's committed goal identity;
- demand/failure/recovery revision increments for a new goal, failed/rejected
  solve, brake/reroute request, or sensing recovery event;
- a successful **new-generation** ordinary moving commit records dispatch time,
  completion time, generation and these revisions.

The pending-goal queue must be checked under its existing mutex, or represented
by an atomic revision pair. Merely checking `gi_.new_goal == false` is not enough.
Do not consume `trajectory_guard_rejection_pending_` just to peek eligibility:
that exchange would steal the event from the existing safety handler. Add a
non-consuming view/revision if needed. Similarly do not consume risk verdicts
in the demand gate; keep their existing 100 Hz handling.

`SUCCESS` without a generation change (e.g. `NO_NEED` backup), failed solves,
rest-to-rest recovery and PlanFromRest must not renew an ordinary skip lease.

### 3. Cross-map renewal

The smallest first implementation permits skip only when geometry certificate,
receipt, and current map all match. This may save little: a 10 Hz map feed can
still force roughly 10 Hz solves. Useful reuse across publications requires:

1. Existing 100 Hz geometry guard has certified this exact current generation
   against the current fresh map; if not, do not skip.
2. In the 15 Hz replan callback, renew the stop-viability receipt for the current
   generation/current trajectory time against one unchanged current map.
3. Renewal interval covers at least the next possible solve completion plus a
   reserve. Reusing the full existing 2 s horizon is simplest and must be profiled;
   viability has so far been a much smaller cost than EXP/backup optimizers.
4. Do not time-scale/modify/commit the trajectory during renewal. A renewal failure
   simply disallows deferral and proceeds through existing replanning/guard paths.
5. Recheck generation, map, goal/recovery revision after renewal. A changed input
   invalidates the result rather than retrying indefinitely in this callback.

This work must not run on the 100 Hz main FSM or command timer. If renewal proves
expensive, use a separate bounded latest-only validator; the replan callback may
read only an exact-matching completed receipt. Missing/stale result means no skip.

## Eligibility: all conditions required

| Gate | Required for suppressing this solve |
|---|---|
| Mode/policy | Guard enforcement and viability enabled; common policy/config in Full and Adaptive. |
| FSM | Ordinary FOLLOW_TRAJ, no stop/finished/PlanFromRest/certified rest-to-rest episode; initial implementation excludes clearance-escape/initial-footprint-egress certificates rather than silently reusing their special origin allowance. |
| Goal/demand | No queued or accepted new goal; committed goal revision matches; no new failure/rejection/recovery demand since the last valid ordinary commit. |
| Sensing recovery | No pending event-recovery sequence; no recovery-announced episode or unresolved Full-refresh request/ACK/route requirement. Full absent-gate default does not masquerade as pending work. |
| Runtime state | No active/unfinished safety brake, pending revalidation, or already executing backup; retain all existing hazard consumers and command gates. |
| Geometry certificate | Explicit SAFE, exact generation/current fresh map, finite interval covering current time through the next-solve reserve; preserve stricter motion freshness check. |
| Viability receipt | Valid, every state evaluated, same generation/start/policy/current map, actual checked interval covers required continuation reserve. |
| Trajectory margin | Nonempty finite command sample; not finished; remaining trajectory and EXP-before-backup horizon exceed the same reserve. |
| Time budget | Nominal next callback plus jitter reserve still fits the fixed deferral cap measured from last successful ordinary solve dispatch; no failed attempt resets it. |
| Final race check | Generation/map/demand revisions/FSM/brake state unchanged after all evidence is collected. Otherwise no skip. |

For backup margin use the earliest relevant boundary: appended backup start;
if a carried-backup interval is ahead, its start; if currently inside any backup,
do not skip. `has_appended_backup=false` does not authorize unlimited following:
the trajectory-end and viability deadlines still apply. Do not read
`last_exp_traj_info_` unprotected from the FSM; put needed metadata in the coherent
command snapshot or expose it through the planner's lock.

## Timing arithmetic (both clocks explicit)

Let P be the actual configured replan timer period (currently integer milliseconds,
about 0.066 s), J a conservative scheduling allowance, B the bounded solve/commit
budget, and C a command/guard handoff reserve. Initially preserve the configured
solver budget (`replan_forward_dt=0.1 s`, existing overtime threshold 0.09 s) and
use at least two 10 ms command ticks for C. These are engineering budgets, not
hard-real-time guarantees.

For a single skipped callback, require geometric/viability/EXP coverage through
`current_tt + P + J + B + C`, and require the next expected dispatch
`steady_now + P + J` no later than the fixed 0.20–0.25 s dispatch deadline.
This naturally resumes solving before a backup stitch/trajectory end rather than
waiting until the deadline is crossed. A more conservative reserve can reduce
eligible skips; measure it rather than loosening certificates to obtain savings.

Keep steady-clock dispatch age separate from simulator trajectory time. On a
nonfinite timestamp, backward simulation-time jump, generation/start mismatch or
unexpected scheduling overrun, invalidate the lease and do not skip. A wall timer
can be delayed by the OS, so this policy bounds *intentional deferral decisions*,
not worst-case real wall latency. Strict hard deadlines would need a wakeup/watchdog
design; existing 100 Hz map/command safety gates must remain live regardless.

If renewal or solving overruns, never extend a receipt's checked-until field or
hold the old trajectory merely to lower mean CPU. Existing safety revalidation,
braking and no-path stopped recovery retain authority. A new lease-expiry monitor,
if required to enforce execution within receipt coverage under scheduler stalls,
must be designed explicitly rather than implied by the 15 Hz timer.

## Minimal implementation shape, later only

1. Persist coherent receipt metadata and add a read-only command-evidence API.
2. Add a pure `DemandReplanDecision` helper with explicit reason enum. Unit-test
   combinations without ROS. Default feature disabled.
3. In replan callback, keep all existing early safety gates, collect evidence,
   optionally renew receipt on the current map, and skip only when helper permits.
4. Existing `callReplanOnce`, post-replan rejection/geometry handling and 100 Hz
   functions remain unchanged. Add non-consuming outcome/revision bookkeeping.
5. Log aggregate decision counts and maximum dispatch gaps at about 5 s intervals,
   not every point/timer tick. Include actual receipt gen/map/interval when needed
   for an audit, and report timer invocations separately from solver invocations.

## Required tests before any performance claim

- Valid ordinary same-generation/current-map case skips; every individual gate
  invalidation forces the existing path instead (including SAFE vs DISABLED).
- New pending goal before main-FSM consumption, accepted goal during renewal,
  rejected/failed solve with unchanged generation, and SUCCESS/NO_NEED without
  a commit all forbid lease renewal.
- Appended backup approaching, currently on carried backup, carried interval
  ahead, EXP-only fallback near checked-until, short remaining trajectory.
- Clearance-escape/initial-footprint-egress certificate cannot qualify as an
  ordinary receipt or lose its origin-specific semantics during renewal.
- Final scaled candidate receipt has correct TT horizon; initial state-check
  failure cannot produce a valid receipt; old generation receipt never matches.
- Map changes during or immediately after renewal; multiple map versions during
  the sampled stop loop; unchanged occupancy version with fresh processed scans;
  stale map, revalidation request, command-generation mismatch.
- Snapshot/goal/recovery race after evidence collection; no consumed safety events.
- Deferral arithmetic around exact deadline, one timer tick, solver budget,
  sim-time reset/nonfinite values, delayed callback/overrun; failures cannot
  perpetually reset the deadline.
- Fake-clock tests show 100 Hz guard/command invocations are never reduced by
  demand decisions; real logs compare actual rates, p95/p99/max inter-command
  gaps, map age, replan dispatch/commit gaps and event-to-Full/ACK latency.
- Matched Full/Adaptive seed1 n=1 first: both complete/contact0, no path without
  fresh observation+map ACK+new certificate, time/velocity/path quality retained.
  Reject a candidate whose travel time grows >10% versus matched Full or whose
  CPU reduction relies on waiting. Then repeat before widening maps/repetitions.

Use CPU accounting identical to prior candidates and report both mean process
CPU and cumulative core-seconds, with renewal CPU included. An ablation must
apply the same common demand policy to Full; do not compare optimized Adaptive
against deliberately unoptimized Full. The current evidence does not predict
that this policy alone can reach the user's 40% target.
