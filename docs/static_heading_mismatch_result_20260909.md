# Static heading-mismatch / blind-fork exploratory result

Date: 2026-09-09 (Asia/Seoul)

Decision: **exploratory safety separation observed at the frozen severe 2 Hz
dropout-equivalent stress; do not describe it as a nominal-rate or population
guarantee.**

## Question and scope

The experiment asks whether the deployed Adaptive frontend can recover safety
that a fixed 45-degree body-heading Sector loses in a realistic static scene.
The background point cloud is always present, all obstacles are static, Full
has an inflation-feasible bypass, and the hazard is initially outside the
body-fixed Sector but inside the northbound velocity sector. SUPER planner
logic, v7 speed, 1.5 m omnidirectional near-field bubble, guard thresholds and
all three policy implementations were left unchanged.

The final `shm1_h9` scene starts at `(24.5,0,1.5)` facing west and flies north
to `(24.5,20,1.5)`. Outer walls bound x=20..28, a divider at x=23.5 from
y=2..15 creates two branches, and a static transverse wall at y=4 closes the
east branch. Full can see that closure before selecting a branch. Fixed Sector
omits it until the 1.5 m near-field bubble receives it. H9 changes only the
common simulated LiDAR cadence from h8's 4 Hz to 2 Hz; it is therefore a
severe dropout-equivalent robustness condition, not the normal 10 Hz profile.

## Frozen development trail

| Version | Single purpose/change | Full | Fixed Sector | Adaptive | Decision |
|---|---|---:|---:|---:|---|
| h1 | broad cylinder, heading mismatch | safe 4.85 s | safe 5.09 s | safe 5.15 s | wall silhouette entered Sector |
| h2 | narrow pole | safe 4.72 s | safe 4.93 s | safe 4.94 s | trajectory dispersion missed pole |
| h3 | transverse wall, attempted held yaw | safe 4.95 s | safe 10.00 s | safe 5.81 s | mission stack rotated yaw |
| h4 | wall endpoint x=23→24 | safe 5.24 s | safe 4.66 s | safe 5.14 s | 1.5 m near-field bubble stopped Sector |
| h5 | two-branch topology, closure y=8 | **timeout 60 s** | not run | not run | mandatory Full gate failed |
| h6 | closure y=8→4, 10 Hz | safe 4.44 s | safe 12.38 s | safe 5.46 s | Sector backtracked; time separation only |
| h7 | common cadence 10→5 Hz | safe 5.68 s | safe 10.14 s, 0.177 m | safe 6.00 s, 0.632 m | clearance/time separation only |
| h8 | common cadence 5→4 Hz | safe 5.21 s | safe 14.47 s | safe 6.85 s | scan phase dominated one row |
| h9 | common cadence 4→2 Hz | safe | contact in smoke | safe | mechanism pass; repetition allowed |

All failed candidates and stop decisions are retained. H9 did not change the
map, near-field radius or planner after observing h8; its sole changed factor
was frozen in the preregistration before generation and flight.

## Prerequisite gates

The actual-PCD structure gate passed. The inflated west bypass exists, the
direct route has -0.1886 m body clearance, body-fixed visibility is 0 points,
and velocity-aligned visibility is 7,074 points.

The actual MARSIM raycast and production C++ frontend replay also passed using
identical 2 Hz raw input:

| Replay metric | Fixed Sector | Adaptive |
|---|---:|---:|
| measured raw frames | 10 | 10 |
| raw hazard points | 23,167 | 23,167 |
| raw trajectory-conflict points | 499 | 499 |
| filtered hazard points | **0** | **23,167** |
| filtered trajectory-conflict points | **0** | **499** |
| consecutive fresh `OCCUPIED` | 0 | **10** |

The clear Fixed-Sector control completed in 4.62 s without contact and
committed a hypothetical hazard-intersecting trajectory (audit clearance
-0.200 m). Hazard Full then completed in 7.64 s with zero contact and 0.662 m
physical clearance. The staged Sector/Adaptive smoke produced one Sector
contact and a contact-free Adaptive completion, permitting repetition.

## H9 repeated result: map `shm1_h9_hazard`, n=10 per mode

These are ten fresh paired run indices with rotating mode order; the earlier
smoke rows are not pooled. Every row was a first-attempt success with valid
resource, speed and static-PCD quality gates. “Safe completion” means mission
completion and zero static-PCD contact.

| Mode | Completion | Contact runs | Safe completion | Mean time (s) | Mean physical clearance (m) | Mean planner ingress (MiB/s) | Mean algorithm CPU (cores) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 10/10 | 0/10 | **10/10** | 8.923 | 0.526 | 2.473 | 0.543 |
| Fixed Sector | 10/10 | **9/10** | **1/10** | 6.534 | -0.141 | 0.705 | 0.496 |
| Adaptive | 10/10 | 0/10 | **10/10** | 9.366 | 0.538 | 2.628 | **0.412** |

Adaptive versus Fixed Sector has nine paired runs where Sector was unsafe and
Adaptive was safe, and zero in the opposite direction. The exact two-sided
McNemar p-value is 0.00390625. Wilson 95% intervals for safe completion are
0.722..1.000 for Full/Adaptive and 0.0179..0.404 for Sector. These intervals
remain wide because n=10 and must not be rewritten as a 100% population
guarantee.

The one contact-free Sector row took 17.85 s: it stopped, searched, backed out
below the fork and used the west branch. It is retained as a real outcome.
The other nine Sector rows contacted the same closure near `(25.03,4.15)`;
their physical clearances were -0.182 to -0.198 m. Thus the reduction is
reproducible but not deterministic.

## What caused Adaptive recovery

The deterministic replay proves the angular component: Fixed Sector removes
the exact hazard/path-conflict samples while Adaptive can retain them and
produce fresh exact verdicts. In natural closed loop, however, Adaptive did
not usually wait for an exact `OCCUPIED` brake. At 2 Hz its map age approaches
the 0.5 s fail-closed boundary, so the already deployed pre-stale refresh and
trajectory-guard recovery paths expose bounded Full information early enough
to select the west topology.

Across the ten Adaptive rows, the filter issued a mean 15.9 pre-stale Full
refresh frames (15.8 committed ACKs), 21.4 Full-refresh requests, one sustained
effective Full-open/trajectory-guard transition and 2.1 replan-guard openings.
Fixed Sector issued none. Adaptive stayed Full-open for 61.4% of time and kept
91.1% of input points in this severe condition. The correct causal statement
is therefore **Adaptive's deployed bounded refresh/recovery policy restored
safety**, not that the exact-risk brake alone caused every avoidance.

## Computation and bandwidth interpretation

Adaptive algorithm CPU averaged 0.412 core versus Full's 0.543 core, a 24.1%
reduction. This is the objective cgroup-v2 algorithm scope, not a summed `top`
percentage. End-to-end CPU was 0.624 versus Full's 0.582 core because the
frontend and simulator-side transport remain part of that broader scope.

The stress condition is intentionally not a bandwidth win: Adaptive planner
ingress was 2.628 MiB/s, 6.3% above Full's 2.473 MiB/s, because frequent
pre-stale/full refreshes dominate at 2 Hz. Fixed Sector used only 0.705 MiB/s
but was unsafe in 9/10 rows. Normal-rate Map1--10 campaigns remain the proper
source for the Full-versus-Adaptive bandwidth claim; H9 is the safety-stress
source. Mixing those claims into one number would be misleading.

## Claim boundary and next evidence

The supported claim is narrow: in a frozen static blind-fork scene under a
severe common cadence degradation, Full and Adaptive were contact-free in
10/10 rows, Fixed Sector contacted in 9/10, and Adaptive used less algorithm
CPU than Full. The result does not prove all-map safety, nominal-rate safety
superiority, or population-level 100% success. A paper should label h1--h9 as
scenario development/exploration and reserve any confirmatory wording for
newly preregistered held-out geometries or real/SITL sensor-dropout validation.

Primary machine-readable evidence:

- `results/static_heading_mismatch_shm1_h9_structure_gate_20260909.json`
- `results/static_heading_mismatch_shm1_h9_replay_gate_20260909.json`
- `results/static_heading_mismatch_shm1_h9_three_mode_n10_raw_20260909.csv`
- `results/static_heading_mismatch_shm1_h9_three_mode_n10_analysis_20260909.json`

