# G1 repair smoke: mission-time and recovery audit

Date: 2026-09-26. This is a read-only audit of **profiled ON, n=1 per mode**,
not an uninstrumented OFF CPU-primary comparison and not a repeatability claim.
No thresholds, source files, geometry, or recorded samples were changed for this audit.

## Evidence

New run directory:

`results/scenario7_repair_smoke_20260926_v1/preflight/gapfree_d1_m01/r01_run60000/`

The table below uses `raw.csv`, each mode's summary, the native observer JSON,
and `artifacts/gapfree_d1_m01_run60000_{mode}.attempt1.stack.log`.
Contact counts are from each `.solid_audit.json`, not sparse-PCD contact counts.

Historical, outcome-disclosed comparison directory:

`results/scenario7_n10_20260925_213533_3120932/test10/gapfree_d1_m01/`

Historical and repair revisions/instrumentation differ. Their values describe
observed behavior; they are not a paired estimate of a patch's causal effect.

## What accounts for Adaptive's 61.30 seconds?

| Metric | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Mission completed | yes | yes | yes |
| Analytic solid contact episodes | 0 | 1 | 0 |
| Mission time, s | 49.97 | 49.55 | 61.30 |
| Recovery episodes | 6 | 7 | 6 |
| Recovery-active duration, s | 4.5399 | 6.2311 | 14.4476 |
| Longest recovery, s | 0.9201 | 1.3202 | 7.0365 |
| Mission time minus recovery-active duration, s | 45.4301 | 43.3189 | 46.8524 |
| Path length, m | 240.324 | 236.644 | 237.392 |
| Moving-candidate handoff rejections | 20 | 14 | 18 |
| Cached-EXP reuse rejections | 2 | 0 | 2 |
| Topology reroute searches | 1 | 1 | 19 |
| Initial-footprint-egress commits | 0 | 0 | 0 |

Adaptive is 11.33 s, or 22.67%, slower than Full in this one triplet. The
recovery-duration difference is 9.9077 s, about **87.4% of that time gap**.
Its path is actually 2.932 m shorter. Thus the dominant observed difference is
recovery dwell, not a longer nominal route or uniformly slower execution.
The subtraction is a timeline decomposition, not a counterfactual speedup estimate.

## Adaptive recovery episodes

Times are taken from paired `TRAJ_GUARD_RECOVERY_SIGNAL active=true/false`
events. ACK delay is recovery activation to `FULL_REFRESH_RECOVERY_ACK`.
An async result's `completed=false` here corresponds to failed candidate
generation/admission with unchanged committed generation; it is not evidence
that a fresh valid path was discarded solely because of an ACK race.

| Cycle | Active duration, s | Full ACK delay, s | Async attempts | Failed attempts before release | Released path |
|---|---:|---:|---:|---:|---|
| 1 | 1.2199 | 0.1305 | 1 | 0 | PlanFromRest/with_backup, generation 4 |
| 2 | 1.0100 | 0.1247 | 1 | 0 | PlanFromRest/with_backup, generation 34 |
| 3 | 0.5109 | 0.0853 | 1 | 0 | PlanFromRest/with_backup, generation 75 |
| 4 | 0.7501 | 0.1188 | 1 | 0 | PlanFromRest/with_backup, generation 91 |
| 5 | 3.9202 | 0.1209 | 8 | 7 | certified_local_escape, generation 109 |
| 6 | 7.0365 | 0.0596 | 14 | 13 | PlanFromRest/with_backup, generation 110 |

Cycles 5 and 6 consume 10.9566 s combined. Their request spacing averages
0.5057 s and 0.5046 s respectively. Individual solves do not consume that full
interval; repeated failed topology/optimization attempts plus the retry policy
account for much of the stationary time. The Full ACKs arrive in about 60–121 ms,
so waiting for sensor transport is not the multi-second bottleneck.

Cycle 5 begins at epoch `1790416354.422482073`, near
`[-24.588, 11.007, 2.147]`. Ordinary backup and stopped candidates are rejected
with `CLEARANCE_MARGIN`. Six reroute searches and three failed EXP generations
precede the generation-109 local escape at epoch `1790416358.336840235`.
That escape lasts 1 s and moves roughly 0.6 m.

Cycle 6 begins at epoch `1790416359.375956069`, after that local escape finishes,
near `[-24.63, 10.43, 2.15]`. The local escape itself ends with a SAFE certificate;
the next PlanFromRest candidate and certified-stop fallback are rejected for
`CLEARANCE_MARGIN`. Twelve reroute searches, optimizer failures, and repeated
inflated-map `A* NO_PATH` results follow. A generation-110 path is finally
released at epoch `1790416366.412412806` (recovery deactivation).

This is a conservative recovery/liveness cost. The record does not show a
new unsafe receipt release or a multi-second ACK wait. It does show that a short
local escape can fail to put the robot in a location from which the next route
can be found promptly.

## What the new handoff guard actually rejected

All 20 Full and all 18 Adaptive handoff rejections immediately follow a
same-generation `TRAJ_GUARD_VIABILITY_SLOWDOWN scale=1.250` event. For Adaptive,
candidate age at rejection ranges from 7.366 to 53.404 ms: these are **not**
ordinary candidates rejected merely because they exceeded the 100 ms retained
prefix. Uniform rescaling around a past trajectory start changes the current
position and velocity even while the original retained prefix is still active.

Adaptive handoff errors span 2.200–47.454 mm in position and 0.192–1.400 m/s in
velocity. Full errors span 2.446–50.725 mm and 0.803–1.400 m/s. These are genuine
command-state discontinuities, not merely numerical noise near the 1 mm
continuity tolerance. Adaptive's two cached-EXP rejections would switch by
0.146 m and 1.250 m at the sampled absolute time.

For context, the old G1 r01 Adaptive log has 237 ReplanOnce commits and 15
moving-candidate viability slowdowns; r08 has 246 and 26 respectively. The old
revision did not implement the new handoff test, so a zero historical marker
count would mean “not instrumented/implemented,” not “no discontinuities.”
The old r08 analytic contact followed a measured 0.912567 m pose step in about
10 ms. The new guard addresses that defect class; one clean smoke run does not
prove that all prior contact mechanisms have been eliminated.

## Relation to the historical G1 baseline

Old Adaptive completed times across r01–r10 were
110.58, 48.88, 49.31, 52.79, 51.10, **timeout at 180.01**, 59.97, 52.80, 57.91,
and 51.56 s. Among the nine completed runs only, the median was 52.79 s and the
mean 59.433 s; this completed-only statistic deliberately does not hide the
separately stated timeout. The repaired smoke is 8.51 s above that median but
within the prior completed-run range.

The old r01 already accumulated 64.491 s of recovery time and 85 topology
searches. Thus multi-attempt recovery dwell predates the new guard. This single
new run cannot establish whether the stricter, correct handoff rule increases
its probability; it does establish that the current 22.67% Full-relative time
guardrail is not met in this triplet.

## Limits and next optimization target

- **Receipt integration was not exercised:** all three runs have zero
  initial-footprint-egress commits. These flights cannot validate the repair
  for the old r06 repeated-egress-commit timeout, nor attribute their elapsed
  time to that receipt's hot-path cost.
- Keep the handoff rejection invariant. Relaxing it would re-admit measured
  position/velocity discontinuities. A future retiming design would need to
  preserve the current command PVA and the retained prefix, then regenerate
  or smoothly retime the future segment.
- Independently audit the repeated stopped topology choices in cycles 5/6,
  and whether local-escape endpoint selection can establish a useful onward
  route. Do not remove the safety certificate or simply classify these failures
  as successful recovery.
- Additional prospective trials and uninstrumented OFF runs are necessary
  before making repeatability or CPU-reduction claims. Frozen smoke evidence
  remains unchanged.
