# Static blind-doorway c1--c3 exploratory result

Date: 2026-09-09 (Asia/Seoul)

Decision: **`STOP_C1_C3_NO_STATIC_SAFETY_SEPARATION`**

## Question and scope

This experiment asked whether a realistic static L-corridor/doorway could
produce the missing safety mechanism evidence without changing SUPER or the
Full/Sector/Adaptive policies:

1. the background point cloud remains continuously observable;
2. a static cylinder is hidden from the 45-degree fixed Sector but present in
   the raw 360-degree scan;
3. the clear control naturally commits a trajectory that would intersect the
   cylinder;
4. an inflation-aware Full bypass exists; and
5. Adaptive's raw future-trajectory worker detects that exact hazard before
   contact.

The maps are exploratory design data. They are not pooled with Map1--10,
`abt*`, or any future confirmatory family. No planner, trajectory optimiser,
guard decision, filter angle or deployment profile was changed. C3 adds one
scenario waypoint file, not planner code.

## Fixtures and staged changes

All three candidates use the same full-height L-corridor. The three clear PCDs
are byte-identical (SHA-256
`4b1d325a457c434d4a186d961eef8a6783915e84c946bb6413622cf8ee6d90d9`).
The hazard member adds one static cylinder and changes no background points.

| Candidate | Mission | Static cylinder `(x,y,r)` m | Change motivated by prior observation |
|---|---|---:|---|
| c1 | `(24,24) -> (0,24)` | `(18.4,23.3,1.2)` | initial independent doorway design |
| c2 | same | `(19.8,23.0,0.9)` | reduce angular width and move toward the occluding corner after c1 exposed another edge early |
| c3 | direct `(0,24)` goal | same as c2 | remove the artificial stop/yaw scan at the corner waypoint |

Each generated pair passed a fail-closed actual-PCD structure gate. The hazard
member contains only a positive added cylinder set; the body-inflated nominal
outgoing line intersects it; every ROG-like inflated route segment has a path;
minimum route-to-sampled-surface distance is 1.05 m; and the outgoing Sector
has hundreds of background support points at x=20/12/4. C1's actual MARSIM
liveness replay also retained 5,048.88/4,232.06/3,204.80 points per frame at
those stations.

## Measurement correction

The first clear control exposed a measurement-only defect: committed
trajectory visualisation markers were disabled, so the audit returned null
despite receiving polynomial messages. `native_loop_monitor.py` now evaluates
the exact `PolynomialTrajectory` coefficients, generation start wall time and
current-to-1.0-second interval using the same coefficient order and 0.01 s
sampling as the C++ worker. This does not publish planner input.

A second attribution defect was found in c3. A generic exact OCCUPIED verdict
can be caused by any raw obstacle in the future trajectory crop, including the
L-corridor wall. The monitor now separately counts a verdict only when its
witness position body-intersects the declared static cylinder. The original
generic count remains unchanged and visible.

The invalid marker-dependent clear row was preserved separately and was not
used in the table. Likewise, the first c2 Adaptive replay accidentally used a
diagnostic two-point CIRI minimum; it was rejected before analysis and replaced
by the explicitly named `adaptive_min200` row below. Neither invalid diagnostic
contributes to a gate.

## Actual raycast/frontend component gate

Before c2 flight audit, a fixed-state actual MARSIM replay at
`(24.0,21.7,1.5)`, yaw 90 degrees and velocity `(0,7,0)` used the production
C++ crop/risk frontend and the deployed `risk_min_points=200` threshold. The
trajectory ended at `(19.512156,23.567351,1.5)` after 1.0 s.

| Component metric | Fixed Sector | Adaptive raw-risk |
|---|---:|---:|
| raw hazard-visible frames | 50/50 | 51/51 |
| raw trajectory-conflict frames | 50/50 | 51/51 |
| filtered hazard points | 0 | 0 |
| filtered conflict points | 0 | 0 |
| fresh exact OCCUPIED | disabled | 26 |
| maximum consecutive fresh OCCUPIED | disabled | 26 |

All 13 component checks passed. This proves actual raycast visibility, Sector
exclusion and raw-worker operation at that state. It is not a closed-loop
safety result.

## Closed-loop exploratory result

All rows below are unique first attempts, speed-valid and static-PCD contact
free. `Committed clearance` is against the declared cylinder: a negative value
means at least one sampled 1.0-second committed trajectory intersected it,
even if a later replan avoided physical contact.

| Candidate/map/mode | Complete | Time (s) | Contact | Physical hazard clearance (m) | Committed clearance (m) | Generic exact OCCUPIED | Hazard-matched exact |
|---|---:|---:|---:|---:|---:|---:|---:|
| c1 clear / Sector | yes | 10.43 | 0 | -- | -0.200 | 0 | -- |
| c1 hazard / Sector | yes | 9.90 | 0 | +0.592 | +0.584 | 0 | -- |
| c1 hazard / Adaptive shadow | yes | 11.63 | 0 | +0.658 | -0.200 | 1 | 1 (legacy single-witness classification) |
| c2 clear / Sector | yes | 10.21 | 0 | -- | -0.200 | 0 | -- |
| c2 hazard / Sector | yes | 9.43 | 0 | +0.780 | +0.619 | 0 | -- |
| c3 clear / Sector | yes | 15.00 | 0 | -- | -0.200 | 0 | -- |
| c3 hazard / Sector | yes | 14.01 | 0 | +0.704 | **-0.190** | 0 | -- |
| c3 hazard / Adaptive shadow | yes | 11.76 | 0 | +0.624 | +0.155 | 2 | **0** |

C3 hazard/Sector and Adaptive-shadow were each repeated once only because the
measurement definition changed, not because of their outcome. The original
surface-probe Sector row was also safe (+0.735 m), and the pre-attribution
Adaptive row was safe (+0.540 m). Both are preserved; the table uses the later
whole-cylinder probe and hazard-matched-counter rows. No outcome was replaced
inside a campaign and all underlying attempts were first attempts.

The clear controls succeeded in their intended role: all three naturally
committed a hypothetical cylinder-conflicting trajectory. Nevertheless, every
hazard Sector row also completed without contact. C1/c2 saw enough of another
cylinder edge to select a northern bypass. C3 removed the corner waypoint and
the fixed Sector did transiently commit a conflicting trajectory while moving
5.63 m/s, but the ordinary map/replan loop replaced it before contact and kept
0.704 m physical clearance.

C3 also explains why the generic exact count is unsafe to interpret. Its first
Adaptive exact witness was `(21.8865,1.6730,1.7382)`, on the long inner wall
near mission start rather than the cylinder at `(19.8,23.0)`. Repeating after
adding hazard attribution produced generic exact=2 but hazard-matched exact=0.
C1 produced only one hazard-matched verdict, below the frozen two-period
requirement, and four ordinary replan Full openings had already occurred.

## Decision and scientific boundary

The final gate passed the clear-control and deterministic component checks but
failed both required closed-loop checks: Sector-degraded candidates = 0/3 and
candidates with at least two hazard-matched exact verdicts = 0/3. No Full-only
flight, protected Adaptive flight, repeated campaign or McNemar test follows.
These rows do not support an Adaptive collision-safety-rate advantage.

Continuing to move the same cylinder after observing each outcome would be
result-directed scenario tuning. The next admissible choice is therefore
explicit rather than automatic:

- if a safety-superiority claim is mandatory while policies remain frozen,
  preregister a fundamentally different **two-route static doorway topology**
  with a decision point before reveal, use the new hazard-matched audit, and
  reserve independently generated replicas for confirmation;
- if the baseline may change, add a fixed velocity-aligned Sector ablation and
  rerun a newly preregistered comparison, because the present fixed Sector uses
  anticipatory body yaw while Adaptive uses velocity heading; or
- retain the current paper's strongest supported claim: Full-level empirical
  safety/completion with lower computation/bandwidth, without claiming a
  statistically demonstrated safety advantage over Sector.

## Reproducibility

- final gate: `results/static_blind_doorway_c1_c3_exploration_gate_20260909.json`
- structure gates: `results/static_blind_doorway_sbd1_c{1,2,3}_structure_gate_20260909.json`
- c2 replay gate: `results/static_blind_doorway_sbd1_c2_replay_gate_20260909.json`
- raw closed-loop rows: `results/static_blind_doorway_sbd1_c*_audit*_20260909.csv`
- generators/manifests: `scripts/native_campaign/gen_static_blind_doorway_*.py`,
  `scripts/native_campaign/static_blind_doorway_*manifest.json`
- audit/analyzers/tests: `scripts/native_campaign/trajectory_audit_math.py`,
  `native_loop_monitor.py`, `analyze_static_blind_doorway_exploration.py`

Python compilation, 18 focused pytest assertions and all 26 unittest-discovery
tests passed. `mission_planner` rebuilt successfully after installing the c3
scenario waypoint. Runtime SUPER remains based on commit
`2ad3419c127a617c6d7df6925e81a14175a9c096` and must not be pushed upstream.
