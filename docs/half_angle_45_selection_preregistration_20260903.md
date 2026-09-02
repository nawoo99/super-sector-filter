# Selection and confirmatory-use record for the 45-degree half-angle

Date frozen: 2026-09-03 (Asia/Seoul)

## Decision

The next controlled side-entry topology experiment will use a common nominal
half-angle of 45 degrees for Sector and Adaptive. Full remains the unfiltered
360-degree reference. The angle is now frozen before the side-entry topology
flight results are observed.

## Why 45 degrees was selected

The 2026-09-02 60/45/30-degree campaign was exploratory. It did not produce a
completion or collision difference: Sector and Adaptive both completed 27/27
without a static-PCD collision. The angle is therefore not selected because it
already demonstrated a safety-rate advantage.

Forty-five degrees provided the most informative balance among the secondary
screening metrics:

- Sector produced two of nine descriptive low-clearance rows below 0.20 m,
  whereas Adaptive produced zero; the worst-clearance difference favored
  Adaptive by 0.053 m, the largest of the three angles.
- Adaptive reduced mean mission time by 5.450% relative to Sector, also the
  largest of the three angles.
- Adaptive reduced measured DDS rate by 21.313%, retaining a material
  communication difference.
- Sixty degrees had a larger DDS reduction (25.852%) but no low-clearance
  separation. Thirty degrees had a smaller DDS reduction (15.133%), did not
  improve the primary outcome and increased both algorithm and end-to-end
  core-seconds relative to Sector in this screen.

Thus 45 degrees is an operating-point choice based on margin, time and
communication balance, not a post-hoc claim of improved completion or collision
rate.

## Evidence separation

The 54 rows used to choose the angle remain exploratory and must not be pooled
into the confirmatory side-entry result. Only flights run after the topology,
code, profiles, metrics and stopping rule are frozen may be labelled
confirmatory.

The primary outcomes remain:

1. mission completion;
2. collision occurrence, reported separately for the source static PCD and
   the authoritative side-entry-v1 cylinder geometry, with their run-level
   union used as the overall safety outcome.

Secondary outcomes are static-PCD clearance, mission time, DDS cloud plus
verdict rate, ROG compute, algorithm and end-to-end CPU, and Adaptive transition
counts. A 0.20 m clearance cutoff is descriptive and is not a collision label.

## Next experiment boundary

The side-entry topology will be a deterministic relative-geometry overlay on
the existing Map7/Map9/Map10 loop, not a new random-map generalization study.
One identical placement rule will be applied without per-map outcome tuning.
If the rule changes after a flight, it becomes a new explicitly versioned
exploratory topology; failed rows are never deleted or relabelled.

Initial screening will use one Full/Sector/Adaptive run on Map7, followed by a
rotating Map7/Map9/Map10 n=3 campaign only if the geometry and runtime gates
pass. The per-call optimizer phase trace will be disabled for performance
comparisons; cgroup and ordinary memory accounting remain enabled. OOM
reproduction is a separate diagnostic experiment.

## Frozen side-entry-v1 rule (recorded before flight)

The overlay is a late-appearing, stationary vertical cylinder generated at the
simulator's common raw-sensor source. It is appended before the Full raw-DDS
publisher and before the Sector/Adaptive in-process handoff split. Consequently
all three modes receive the same source implementation, while Sector/Adaptive
retain the C++ sensor-front-end architecture used in the preceding campaigns.
The feature is disabled by default and enabled only by the three explicitly
named `seed{7,9,10}_side_entry_v1.yaml` profiles.

A purely static PCD overlay was rejected before flight. With a 15 m sensing
horizon and a persistent occupancy map, an obstacle needed after a turn can be
inserted during the preceding approach, so the experiment would not isolate
the short angular-information-loss interval. The late-appearance condition is
therefore part of the topology definition, not a result-driven parameter
change.

The single cylinder is generated only at the first loop corner `(24, 24)` when
all of the following mode-blind geometric predicates hold continuously for
0.02 s:

1. horizontal speed is at least 2.0 m/s and the vehicle is within 2.0 m of the
   corner;
2. the 0.8 s PVAJ command prediction is 0.8--3.5 m from the vehicle;
3. body-yaw/velocity-yaw mismatch is at least 50 degrees;
4. after at most a 20 degree nudge toward the already blind side, the complete
   cylinder has a body-relative inner edge of at least 47 degrees: the frozen
   45 degree half-angle plus a 2 degree margin;
5. the complete cylinder remains inside the velocity-aligned 45 degree sector;
6. its centre is within 2.0 m of `(24, 24)`.

The cylinder radius/height are 0.25/3.0 m, its surface sampling is 0.05 m
azimuthal by 0.10 m vertical, the visibility horizon is 15 m, and tagged
intensity is 14545. It persists after appearing. Placement uses measured
geometry only; it does not read filter mode, full-open state, planner result,
collision state or previous campaign outcomes.

The original Map7/Map9/Map10 manifests put the nearest existing obstacle
surface 2.581878/2.869060/2.800504 m from the first corner. The new cylinder's
farthest possible surface is 2.25 m from that corner, giving guaranteed
source-obstacle gaps of 0.331878/0.619060/0.550504 m respectively. Thus a
side-entry contact cannot be attributed to overlap with an existing random
cylinder. One small cylinder and the common clear disk also leave bypass
topology for the Full reference; the Map7 one-run gate must still confirm that
the implemented planner can use it.

`scripts/native_campaign/validate_side_entry_v1.py` enforces equality of the
three configuration blocks, the manifest separation, and the per-run body/
velocity angular predicates. A row is invalid rather than safe if no valid
spawn event is produced. Collision is computed analytically as intersection of
the 0.20 m vehicle sphere with the solid tagged cylinder, independently of raw
DDS publication or rendered point sampling. Static-PCD and side-entry contacts
are both retained in the raw record.

## v1 feasibility-gate result and frozen v2 correction

The first Map7 Full/Sector/Adaptive gate was run only after commit `18e092e`
had frozen and published v1. All three modes completed without a source-static-
PCD contact, but all three rows are invalid for the side-entry experiment
because no spawn event occurred:

| Map | Mode | Complete | static PCD contact | side-entry spawned | valid row |
|---|---|---:|---:|---:|---:|
| Map7 | Full | 1/1 | 0 | 0 | 0/1 |
| Map7 | Sector | 1/1 | 0 | 0 | 0/1 |
| Map7 | Adaptive | 1/1 | 0 | 0 | 0/1 |

These rows are retained in
`results/side_entry_v1_map7_three_mode_n1_raw_20260903.csv`; they are neither
safe side-entry trials nor evidence of no mode difference.

Two Full diagnostic reproductions left every v1 generation predicate unchanged
and added counters/logs only. In the final trace, 17 candidates passed the
prediction-distance, yaw-mismatch and nudge gates. All 17 were completely
outside the body sector. The first four were also completely inside the
velocity sector, but their corner distances were 3.096613--3.633480 m and thus
failed the 2.0 m clear-disk condition. Later candidates approached a minimum
2.592393 m corner distance only after their velocity-relative outer edges had
grown beyond 45 degrees. No sample could satisfy both predicates, so v1 was
geometrically unrealizable on the observed Map7 turn.
The 17 candidate rows are preserved in
`results/side_entry_v1_map7_full_candidate_geometry_20260903.csv`.

`side-entry-v2` is now frozen before any v2 flight. It changes exactly one
generation value: PVAJ prediction is reduced from 0.8 s to 0.6 s. The 45 degree
half-angle, 2 degree margin, speed/mismatch/hold predicates, 0.8--3.5 m trigger
distance, 2.0 m trigger and trap clear disks, maximum nudge, one-cylinder
radius/height/sampling, common-source injection, analytic collision oracle and
stopping rule are unchanged. This is a feasibility correction motivated by an
empty v1 treatment, not by a completion or collision outcome after exposure.
V1 and v2 rows must never be pooled.

The 0.6 s value is not a collision-rate sweep: it is the previously implemented
PVAJ horizon used by the old turn diagnostic and is the nearest pre-existing
discrete value below the failed 0.8 s condition. The v2 Map7 three-mode n=1
gate remains an integration gate. It is valid only if every mode produces an
event satisfying the 47 degree body inner edge, 45 degree velocity outer edge,
2.0 m clear-disk and source-gap checks. Only after that gate may the frozen v2
rule expand to the predeclared rotating Map7/Map9/Map10 n=3 campaign.

The first pre-fix v2 Map7 gate also remains an invalid three-row integration
attempt. A candidate had body inner edge printed as exactly 47.000000 degrees,
velocity outer edge 6.702704 degrees and corner distance 0.904123 m, yet the
body predicate returned false because the constructed angle differed from its
boundary by floating-point roundoff. No v2 obstacle was exposed in any of the
three modes. The raw rows are retained in
`results/side_entry_v2_map7_three_mode_n1_raw_20260903.csv`.

Before the next v2 flight, the implementation comparison was fixed with a
`1e-9` radian tolerance (and `1e-9` m for the clear-disk comparison). This does
not change the declared 47/45 degree or 2.0 m geometry at reportable precision;
it only makes a value constructed on the declared boundary satisfy that same
boundary. The tolerance fix is versioned in source and must be published before
the next gate. These pre-fix invalid rows are not pooled with the post-fix v2
sample.

The post-tolerance v2 gate was also invalid in all three modes. Full produced
three consecutive geometry-valid command samples but their measured span was
0.019887 s, just below the exact 0.02 s wall-clock hold. Sector and Adaptive
did not produce a joint geometry-valid sample because their mode-dependent
PVAJ prediction centres remained outside the 2.0 m clear disk when the angular
predicates held. No side-entry obstacle was exposed, so this remains a
treatment-feasibility result rather than a safety outcome. The rows are kept in
`results/side_entry_v2_map7_three_mode_n1_postfix_raw_20260903.csv`.

## Frozen side-entry-v3 rule (recorded before v3 flight)

V3 removes the remaining mode-dependent placement variable. Instead of making
each mode's current PVAJ prediction the obstacle centre, every Map7/Map9/Map10
run uses the exact world-frame centre `(22.5, 23.0)` at the first corner. The
same body-outside, velocity-inside, speed, mismatch, trigger-distance and
corner-region predicates must still be satisfied before the obstacle appears.
Nudging is disabled (`0` degrees), so an event cannot alter that common centre.

The hold is explicitly 0.015 s. This value requires three nominal 100 Hz
command samples while avoiding the v2 mistake of equating a 20 ms continuous
threshold to two real timer intervals that can total slightly under 20 ms. No
completion or collision observation informed this change because neither v1
nor v2 exposed an obstacle.

The fixed centre is 1.802776 m from `(24, 24)` and its radius is unchanged at
0.25 m, so its farthest surface is 2.052776 m from the corner. Relative to the
source manifests, the guaranteed Map7/Map9/Map10 gaps are therefore
0.529103/0.816285/0.747729 m. The 45 degree half-angle, 2 degree body margin,
one-cylinder geometry, 15 m visibility horizon, common-source injection,
analytic 0.20 m vehicle-body collision oracle and all performance settings are
unchanged. The Map7 Full/Sector/Adaptive n=1 gate is still an integration gate;
all three rows must spawn exactly at `(22.5, 23.0)` and pass the event validator
before any Map7/Map9/Map10 n=3 expansion.

## v3 integration-gate result and frozen v4 correction

The v3 Map7 gate showed that fixed-world placement removed most, but not all,
mode dependence. Full and Adaptive both spawned the cylinder exactly at
`(22.5, 23.0)`, completed, and had zero source-static-PCD and analytic
side-entry contacts. Sector completed with zero source-static-PCD contact but
did not spawn the cylinder, so its row is invalid as a side-entry trial.

| Map | Mode | Complete | static contact | side-entry spawned | side-entry contact | valid row | time (s) |
|---|---|---:|---:|---:|---:|---:|---:|
| Map7 | Full | 1/1 | 0 | 1 | 0 | 1/1 | 75.61 |
| Map7 | Sector | 1/1 | 0 | 0 | n/a | 0/1 | 79.47 |
| Map7 | Adaptive | 1/1 | 0 | 1 | 0 | 1/1 | 68.14 |

The failure was caused by the remaining `velocity-inside` spawn predicate.
At the common fixed centre, Sector's valid samples had the cylinder completely
outside the body-fixed 45 degree crop, as intended, but its velocity-relative
outer edge was about 95 degrees and therefore could not also be inside a
velocity-aligned 45 degree sector. That predicate is not an input requirement
of the implemented Adaptive method: Adaptive's risk worker consumes the common
360 degree raw sensor stream and can request a full-map refresh independently
of the body-fixed filtered cloud. Requiring velocity inclusion at obstacle
generation therefore makes treatment assignment depend on the mode's command
trajectory and excludes precisely the side-entry case under study.

The v3 rows are retained in
`results/side_entry_v3_map7_three_mode_n1_raw_20260903.csv` and must not be
pooled with later versions.

Side-entry-v4 is frozen before its first flight. It preserves the exact v3
world centre `(22.5, 23.0)`, cylinder radius/height, trigger corner, speed and
body-yaw/velocity-yaw mismatch thresholds, 0.015 s hold, 0.6 s diagnostic
prediction field, distance bounds, 47 degree body inner-edge threshold,
zero nudge, source separation, common-source injection and analytic collision
oracle. It changes exactly one boolean: `require_velocity_inside: false`.
Velocity-relative angle remains recorded for diagnosis but cannot determine
whether the common obstacle appears. The same source obstacle can consequently
be delivered to Full, hidden from Sector by the body-fixed crop, and observed
by Adaptive's independent 360 degree raw-risk channel.

Because Full and Adaptive have already been exposed once to this obstacle
location under v3, the first v4 Map7 three-mode run is an exploratory treatment
and integration gate, not confirmatory safety evidence. Expansion is allowed
only if all modes produce validator-passing events at the exact fixed centre.
A later repeated campaign must use the frozen v4 implementation and report all
rows, including failures.

## v4 Map7 treatment gate

The first frozen-v4 Map7 run passed the treatment gate in all three modes. All
events used scenario version 4, exact centre `(22.5, 23.0)`, zero nudge,
`require_velocity_inside=false`, a body inner edge above 47 degrees, and a
centre inside the declared 2 m clear disk.

| Map | Mode | Complete | overall contacts | side-entry clearance (m) | valid row | time (s) |
|---|---|---:|---:|---:|---:|---:|
| Map7 | Full | 1/1 | 0 | 0.727 | 1/1 | 102.63 |
| Map7 | Sector | 1/1 | 0 | 0.676 | 1/1 | 65.31 |
| Map7 | Adaptive | 1/1 | 0 | 0.261 | 1/1 | 61.74 |

This establishes common treatment delivery, not the intended mode ordering.
Sector also avoided the obstacle in this single run, while Adaptive had the
smallest side-entry clearance. The result therefore does not yet show Sector
degradation or Adaptive recovery. The predeclared Map7/Map9/Map10 rotating
three-mode n=3 exploratory campaign may proceed without changing v4.

## Source exploratory evidence

- `docs/half_angle_operating_envelope_20260902.md`
- `results/half_angle_sweep_maps7_9_10_sector_adaptive_n3_summary_20260902.csv`
- `results/half_angle_sweep_maps7_9_10_sector_adaptive_n3_reductions_20260902.csv`
