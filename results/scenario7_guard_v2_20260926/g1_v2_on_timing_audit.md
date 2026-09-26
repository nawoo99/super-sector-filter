# G1 guard-v2 ON smoke: Adaptive elapsed-time audit

Date: 2026-09-26. Scope: completed **profiled ON, one run per mode**, read-only
post-run analysis. This is neither an OFF CPU-primary comparison nor a
repeatability/regression claim. No frozen inputs, source files, thresholds, or
flight artifacts were changed. No new flight or benchmark was run for this note.

## Evidence and result

Run directory:

`results/scenario7_guard_contract_smoke_20260926_v2b/preflight/gapfree_d1_m01/r01_run70000/`

Sources within that directory: `{full,sector,adaptive}_summary.json`,
`thread_cpu_summary.json`, and
`artifacts/gapfree_d1_m01_run70000_{mode}.attempt1.{json,stack.log,solid_audit.json}`.
Contact counts below use analytic solid geometry, not sparse-PCD proximity.

| Metric | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Mission completed | yes | yes | yes |
| Solid contact episodes | 0 | 0 | 0 |
| Minimum solid clearance, m | 0.263434 | 0.199560 | 0.240286 |
| Mission time, s | 49.15 | 48.89 | 61.69 |
| Path length, m | 241.413 | 237.300 | 252.351 |
| Recovery-active episodes | 2 | 6 | 13 |
| Recovery-active duration, s | 3.190392 | 5.019967 | 11.347773 |
| Mission minus recovery-active duration, s | 45.959608 | 43.870033 | 50.342227 |
| Moving-candidate handoff rejects | 34 | 55 | 71 |
| Cached-EXP reuse rejects | 7 | 0 | 9 |
| Topology reroute searches | 5 | 1 | 7 |
| Candidate guard rejects | 37 | 29 | 60 |
| Accepted brake commands/holds | 2 | 6 | 13 |
| Rejected brake attempts | 10 | 10 | 29 |
| Initial-footprint-egress commits | 0 | 0 | 0 |

Adaptive is **12.54 s (+25.51%) slower than Full** in this triplet. Its excess
recovery-active duration is **8.157381 s**, approximately **65.05%** of that
time gap. The residual outside recovery-active windows is **4.382619 s**.
Adaptive also travels 10.938 m farther. Braking/reacceleration and the longer
route are plausible contributors to the residual, but these logs do not
uniquely assign that time to either one.

This subtraction is a timeline decomposition, not a counterfactual speedup
estimate. Recovery-active intervals include moving deceleration and cannot all
be described as stationary dwell. All paired intervals close, and all fall
inside the observed mission.

## Adaptive recovery timeline

Intervals pair `TRAJ_GUARD_RECOVERY_SIGNAL active=true/false`. Activation-to-ACK
means the first matching `FULL_REFRESH_RECOVERY_ACK`, not the frontend's
separately reported frame-to-ACK statistic. The first-request column measures
activation to `ASYNC_RECOVERY_REQUEST`, including braking, terminal stability,
map/ACK eligibility, and dispatch admission.

| Cycle | Active, s | First request after activation, s | ACK after activation, s | Async requests | Uncompleted results |
|---|---:|---:|---:|---:|---:|
| 1 | 1.085706 | 1.045403 | 0.145685 | 1 | 0 |
| 2 | 0.399908 | 0.329969 | 0.132963 | 1 | 0 |
| 3 | 1.600302 | 1.050086 | 0.123682 | 2 | 1 |
| 4 | 0.492941 | 0.422951 | 0.100929 | 1 | 0 |
| 5 | 0.562697 | 0.422663 | 0.059852 | 1 | 0 |
| 6 | 0.830535 | 0.699851 | 0.119506 | 1 | 0 |
| 7 | 0.859924 | 0.809861 | 0.126072 | 1 | 0 |
| 8 | 1.070080 | 0.979671 | 0.103003 | 1 | 0 |
| 9 | 0.571570 | 0.431354 | 0.051127 | 1 | 0 |
| 10 | 0.588999 | 0.438841 | 0.054532 | 1 | 0 |
| 11 | 1.250046 | 0.669850 | 0.119423 | 2 | 1 |
| 12 | 0.555296 | 0.445407 | 0.029608 | 1 | 0 |
| 13 | 1.479769 | 0.919782 | 0.125096 | 2 | 1 |

Of Adaptive's 11.347773 recovery-active seconds, **8.665690 s precede each
cycle's first async request**, and **2.682084 s follow those requests** until
release. ACK is already available before the first request in all 13 cycles;
activation-to-ACK spans only 29.6–145.7 ms. These data do not indicate a
multi-second Full sensor/ACK transport stall.

The production `tryAsyncCertifiedRecovery()` admission intentionally requires
the brake to finish, fresh odometry within 0.15 m of the stop position, a stable
position anchor within 0.03 m for 0.25 s, a fresh/eligible map and exact Full
ACK, and at least 0.5 s between attempts. The log split is consistent with
braking/terminal admission dominating these frequent short recoveries; it is
not evidence that the 0.25 s stability condition should be removed.

### Why recovery starts

- Eight live committed-trajectory certificate failures are all
  `CLEARANCE_MARGIN`: cycles 1, 2, 3, 6, 7, 8, 11, and 13. Their reported map
  ages are 3–12 ms, so those activations are not explained by stale-map expiry.
- Five other activations (cycles 4, 5, 9, 10, and 12) follow trajectory finish
  and a rejected `PlanFromRest` candidate. These are also margin failures, not
  a logged global `NO_PATH` condition. Cycle 10 rejects an appended backup and
  then its certified-stop fallback; the other four reject EXP portions.
- There are 60 candidate guard rejections: 51 `ReplanOnce/with_backup`,
  7 `PlanFromRest/with_backup`, and 2 `PlanFromRest/certified_stop_fallback`;
  all report `CLEARANCE_MARGIN`. Not every candidate rejection starts a
  recovery, since a still-certified existing trajectory may continue.
- The 29 rejected brake attempts are not 29 detected physical collisions.
  Twenty-eight show `speed0=0`, `last_dynamics_ok=true`, and
  `last_path_status=SAFE`; stable passive-stop admission still has to succeed.
  The remaining cycle-2 attempt shows `speed0=6.455`,
  `last_dynamics_ok=false`, and maximum velocity 10.337 versus a 7.000 limit.
  Its last sampled path status is `UNOBSERVED`, but that is not evidence that
  unknown space alone caused the rejection. Six stationary holds are accepted.

### Failed/retried async attempts

There are **16 requests, 13 completed releases, and 3 uncompleted results**.
The three retry request spacings are 0.500, 0.510, and 0.510 s, respectively.

- Cycle 3: first solve reports success in EXP generation, but generation-37
  admission rejects an EXP margin violation near `[17.250,24.250,0.550]`.
  The first result is `computed=true completed=false`; generation 36 remains
  current until the second attempt succeeds.
- Cycle 11: first candidate is rejected at its appended backup near
  `[-27.717,-14.421,2.319]`, and the fallback also fails margin validation.
  The first result is `computed=true completed=false`; generation 131 remains.
- Cycle 13: request 15 returns `computed=false completed=false`, with no
  intervening candidate-generation or geometry-failure record. The exact
  dispatch-eligibility/cancellation reason is not logged, so this must not be
  counted as a proven optimizer failure. Request 16 succeeds and advances
  generation 164 to 165 before the cycle closes.

For exact log navigation, Adaptive cycle start/end line ranges are:
974–1016, 1062–1091, 1433–1532, 1621–1654, 1746–1828, 1872–1901,
2523–2558, 2695–2736, 2914–2953, 3195–3236, 3298–3350, 3438–3518,
and 3868–3919. Cycle-13 request 15 is at epoch `1790428924.950192005`;
request 16 is at `1790428925.460288615`.

## Full/Sector switching and correctness checks

The Adaptive strict-recovery audit passes: 13 opened cycles, 13 completed
cycles, no outstanding cycle, matching fresh Full-frame/map ACK and
generation-advancing certified path before release. Frontend reporting records
13 effective Full opens/closes, 111 Full recovery frames out of 640 frames
(17.344%), 638 published frames, 2 stale drops, and no worker overwrites.
That approximately 63.897 s frontend reporting scope is not identical to the
61.69 s mission scope; the frame ratio is not a mission-time Full duty ratio.

All three modes pass the guard-contract audit with exactly one policy marker:

`stop_policy=sampled_unknown_allowed_soft_margin_after_complete_hard_checks stop_policy_revision=2`

This confirms the intended revision was active. It does **not** claim strict
known-free certification, continuous-space safety, or population-level zero
contacts. No initial-footprint-egress commit occurs, so this run does not
exercise the old egress-receipt timeout repair.

## Actual callback rates and stop-validation costs

`thread_cpu_summary.json` reports common periodic windows inside each flight:
Full 45.078964 s, Sector 45.059158 s, Adaptive 55.099022 s. CPU stages are
inclusive and nested: do not add the following rows together, and do not
equate CPU time with elapsed wall time or a callback latency percentile.

| Metric | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Actual main callback Hz | 99.4921 | 99.9575 | 99.4573 |
| Actual command callback Hz | 100.0023 | 100.0019 | 100.0018 |
| Main inclusive CPU, s | 0.428638 | 0.176382 | 0.544177 |
| Main inclusive CPU per call, ms | 0.095571 | 0.039161 | 0.099302 |
| Replan inclusive CPU, s | 9.120628 | 7.381637 | 9.783909 |
| Replan inclusive CPU per call, ms | 13.452253 | 10.855349 | 11.773657 |
| Stop-viability calls | 567 | 586 | 595 |
| Stop-viability inclusive CPU, s | 0.132509 | 0.149578 | 0.141379 |
| Stop-viability inclusive CPU per call, ms | 0.233703 | 0.255253 | 0.237612 |
| Geometry-validator inclusive CPU, s | 0.197140 | 0.213030 | 0.210298 |
| Brake-activation inclusive CPU, s | 0.002475 | 0.006367 | 0.010806 |

All actual-rate, odometry/header/receipt interval, and callback-coverage gates
pass. Callback wall tracing was disabled, so no unrecorded wall p99/max claim
is made. Stop-viability CPU averages about 0.238 ms per call in Adaptive versus
0.234 ms in Full, and totals only about 0.141 s in Adaptive's longer profiling
window. The evidence does not support attributing the 12.54 s mission gap to
the added complete-hard-check traversal's CPU cost or a loss of 100 Hz command
service. The elapsed gap is principally associated with more frequent safety
recoveries, not one long compute invocation.

## Qualitative comparison with v1 ON and next investigation

Historical, outcome-disclosed v1 note:

`results/scenario7_repair_20260926/g1_repair_smoke_timing.md`

The v1 ON triplet observed Full 49.97 s and Adaptive 61.30 s. Its Adaptive had
6 recovery cycles totaling 14.4476 s; the longest was 7.0365 s, with repeated
failed reroutes. This v2 ON run instead has 13 cycles totaling 11.3478 s and a
maximum of 1.6003 s. The near-equal 61.30/61.69 s mission totals therefore hide
different mechanisms: v1 had a few long retry traps, while this v2 sample has
more short stop/restart cycles and a longer traversed path.

These are different revisions and single samples, not a paired causal estimate;
neither improvement nor regression probability can be inferred. Sector is
also contact-free in this triplet, so it does not independently establish an
Adaptive safety advantage.

For a future optimization investigation, preserve all hard checks, Full ACK
identity, terminal stability, and command-continuity checks. First inspect why
executable candidates repeatedly lose their margin under fresh map updates,
and why moving-candidate retiming yields 71 handoff rejections. The guard must
not simply be loosened to make these events disappear. Separately instrument
the specific `computed=false` async eligibility reason if its frequency
persists. Prospective repeated OFF runs remain necessary before a primary
CPU/success-rate conclusion or promotion of this candidate.
