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

## v4 Map7/Map9/Map10 n=3 result

The frozen-v4 rotating campaign produced 27 raw rows. Twenty-six spawn events
were emitted and every emitted event passed the independent validator. Map10
Full run 1 completed but produced no event, so it is retained as an invalid
side-entry row. The cause was narrow trigger duration: two geometry-valid
samples spanned only 0.009911 s and did not satisfy the frozen 0.015 s hold.
This is not a collision-free v4 exposure and is excluded from side-entry
outcomes.

| Map | Mode | valid | complete among valid | contact runs | mean side clearance (m) | min side clearance (m) | mean time, all rows (s) | Adaptive effective opens |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Map7 | Full | 3/3 | 3/3 | 0 | 0.863 | 0.621 | 89.64 | 0 |
| Map7 | Sector | 3/3 | 3/3 | 0 | 0.428 | 0.305 | 65.94 | 0 |
| Map7 | Adaptive | 3/3 | 3/3 | 0 | 0.590 | 0.549 | 67.07 | 62 |
| Map9 | Full | 3/3 | 2/3 | 0 | 0.378 | 0.048 | 131.83 | 0 |
| Map9 | Sector | 3/3 | 3/3 | 0 | 0.759 | 0.500 | 79.34 | 0 |
| Map9 | Adaptive | 3/3 | 3/3 | 0 | 0.621 | 0.441 | 78.63 | 44 |
| Map10 | Full | 2/3 | 2/2 | 0 | 0.602 | 0.433 | 113.67 | 0 |
| Map10 | Sector | 3/3 | 3/3 | 0 | 0.472 | 0.175 | 79.96 | 0 |
| Map10 | Adaptive | 3/3 | 3/3 | 0 | 0.579 | 0.517 | 77.40 | 69 |

Across valid rows, Full completed 7/8, Sector 9/9 and Adaptive 9/9; all had
zero analytic side-entry and source-static-PCD contacts. The sole completion
failure was Map9 Full run 2, which stopped at waypoint 3/5 and timed out at
180 s. Its synthetic obstacle clearance was +0.720 m and its stopped position
near `(0.15, -20.16)` was far from the first-corner cylinder. It is therefore
a planner liveness failure, not a side-entry contact. The log contains 218
`PlanFromRest failed` messages, 193 `GeneratePolytopeFromLine failed` messages
and 190 failed backup-generation messages. The current reroute zones and one
vertical recovery attempt repeatedly returned to a start-adjacent CIRI-
infeasible segment with approximately 0.166 m obstacle distance. There was no
OOM kill, cgroup swap growth or PSI pressure during the row.

Sector and Adaptive themselves form nine valid paired rows. Their aggregate
mean side-entry clearances were 0.553 and 0.597 m, a +0.044 m Adaptive change,
but the map-level changes were +0.162/-0.138/+0.108 m on Map7/Map9/Map10.
Sector completed every row and had no contact. Thus v4 still does not establish
the intended Sector degradation or an Adaptive completion/contact advantage;
the small clearance signal is inconsistent across maps.

Resource comparisons against Full use only the seven map/run triples for which
all three modes both received the obstacle and completed. On that comparable
subset, Adaptive reduced external DDS cloud+verdict rate by 29.983%, ROG
per-frame time by 26.009% and delivered point count by 22.093%. It increased
mean algorithm CPU cores by 57.465% and end-to-end CPU cores by 55.166%, so
this campaign supports communication and ROG-work savings, not total CPU
savings. Adaptive effective-Full-open/trajectory-guard-open totals over all
nine runs were 175/60; these are overlapping transition counters, not unique
obstacle episodes.

The v4 campaign should not be expanded to n=10 in its present form. The next
engineering priority is the independent Map9 Full certified-stop liveness
failure. The next topology iteration must also be explicitly versioned: first
add closest-approach context logging, then use the completed v4 trajectories as
declared exploratory design data for one fixed, non-per-run obstacle location,
replace the fragile wall-clock hold with a predeclared sample-count rule, and
freeze a fresh validation cohort. Repositioning the cylinder or changing its
trigger after viewing each new result is prohibited.

Raw and compact evidence are:

- `results/side_entry_v4_maps7_9_10_three_mode_n3_raw_20260903.csv`
- `results/side_entry_v4_maps7_9_10_three_mode_n3_summary_20260903.csv`
- `results/side_entry_v4_maps7_9_10_three_mode_n3_paired_reductions_20260903.csv`

## Source exploratory evidence

- `docs/half_angle_operating_envelope_20260902.md`
- `results/half_angle_sweep_maps7_9_10_sector_adaptive_n3_summary_20260902.csv`
- `results/half_angle_sweep_maps7_9_10_sector_adaptive_n3_reductions_20260902.csv`

## Frozen v5 design-analysis protocol (2026-09-07, before v5 flights)

V4 established common obstacle delivery but did not discriminate the modes,
and one row missed treatment because a 0.015 s wall-clock hold was sensitive to
timer jitter.  V5 is therefore a new experiment, not a continuation that may
be pooled with v4.  No v5 flight may be launched until the following design
procedure has produced one fixed world-frame centre and that centre has been
written below.

The design data are exactly one post-deployment rotating
Full/Sector/Adaptive n=3 rerun on Map7, Map9 and Map10 using the unchanged v4
centre `(22.5, 23.0)`.  Its purpose is to record each trajectory's closest
approach position and the v4 spawn geometry after the stationary-twist fix was
actually installed in `/root/super_ws/install`.  Completion, contact and
clearance labels are not selection inputs.  The previously aborted two-row v4
run was observed while diagnosing the installation mismatch; it is retained
as exploratory evidence but excluded because it used a different deployed
binary.  All 27 post-deployment rows are retained whether or not the mission
completes.  A row without a valid v4 spawn makes the location-design gate fail
rather than being silently discarded.

Candidate centres are the 0.05 m world-frame lattice points that satisfy all
of these predeclared constraints:

1. the candidate is no farther than 0.40 m from the v4 centre;
2. its centre is no farther than 2.0 m from the first corner `(24, 24)`;
3. at every recorded v4 spawn sample its trigger distance is 0.8--3.5 m and
   its complete 0.25 m-radius cylinder has a body-relative inner edge of at
   least 49 degrees (the enforced 47 degrees plus a 2 degree robustness
   reserve);
4. the conservative corner-distance bound leaves at least 0.30 m between the
   new cylinder surface and every Map7/Map9/Map10 source obstacle.

For each candidate and row, the design proxy is Euclidean distance from the
recorded closest-approach position to the candidate, minus the 0.25 m cylinder
radius and 0.20 m vehicle radius.  This is explicitly a local proxy because
the recorded point was closest to the old centre, not a reconstruction of the
whole path.  To prevent choosing a location predicted to trap the references,
every Full and Adaptive proxy clearance must be at least +0.10 m.  Among the
remaining candidates, select lexicographically by:

1. the smallest median Sector proxy clearance;
2. the largest minimum Adaptive proxy clearance;
3. the largest minimum Full proxy clearance;
4. the smallest `x`, then the smallest `y`.

If no candidate satisfies the reference-clearance constraint, v5 location
selection fails; the constraint is not relaxed after looking at outcomes.
Once selected, the same centre is used on all three maps and all three modes.

V5 also replaces the wall-clock hold with exactly three consecutive command
callbacks satisfying every trigger predicate.  The counter resets to zero on
any failed predicate.  The event record must contain required and observed
qualifying-sample counts, and the validator must require both to be at least
three.  V1--v4 retain their original wall-clock behavior.

After the centre, configuration hashes and source commit are recorded, the
only integration gate is Map7 Full/Sector/Adaptive n=1.  Expansion is allowed
only if all three events pass the independent validator at the exact centre.
The frozen confirmatory cohort is then Map7/Map9/Map10, all three modes,
rotating order, n=3 (27 rows).  Every launched row and every infrastructure
retry is reported.  There is no centre, radius, sample-count or trigger tuning
after the first v5 flight.  The primary endpoints remain mission completion
and the union of source-static-PCD and analytic side-entry contact; mode-wise
clearance and Adaptive transitions are secondary endpoints.

## Post-deployment v4 design-gate result and frozen repair sequence

The post-deployment v4 design cohort was run exactly as declared.  All 27
missions completed, but the location-design gate failed because only 26/27
rows received a valid event.  Map10 Full run 1 had 277 near-corner command
samples but a maximum yaw/velocity mismatch of only 3.658694 degrees, so none
passed the frozen 50 degree mismatch gate.  This was not the earlier timer-hold
failure and moving the cylinder cannot repair it because mismatch is
independent of cylinder position.  That row is retained as invalid treatment;
the 26 remaining events are not used to select a new centre under the protocol
above.

All 27 missions completed.  The synthetic cylinder produced zero contacts.
Map10 run 3 Sector had one source-static-PCD contact near `(5.75, 5.75)` at
3.67 s, well before its first-corner side-entry exposure; Full and Adaptive in
the same map/run had no source contact.  This is a real Sector safety outcome
against the source map, not a side-entry-v4 contact and not an infrastructure
failure.  It does not enter the v5 location objective, which remains based on
trajectory geometry only.

Because the declared design gate failed, the next version is split rather
than weakening the gate or dropping the row:

1. side-entry-v5 is an exploratory treatment-instrumentation repair at the
   unchanged centre `(22.5, 23.0)`; it uses exactly three consecutive
   qualifying callbacks, keeps the body-outside geometry gate, and makes the
   yaw/velocity mismatch diagnostic rather than treatment-determining;
2. a Map7 three-mode n=1 integration gate is followed, only if all events are
   valid, by a rotating Map7/Map9/Map10 three-mode n=3 design cohort;
3. all 27 v5 rows must emit a valid event, otherwise the blind-zone experiment
   stops;
4. the already frozen lattice and proxy-clearance algorithm is then applied
   to the complete v5 design cohort, not to the incomplete v4 cohort;
5. the selected centre is recorded before any side-entry-v6 flight.  V6 keeps
   v5's sample-count and diagnostic-mismatch semantics and is the only version
   eligible for the separate n=3 confirmatory cohort.

This repair is based solely on treatment assignment failure.  V5 results are
exploratory and cannot be reported as confirmatory safety evidence.

## Frozen v6 centre and confirmatory boundary (2026-09-07, pre-flight)

The v5 Map7 integration gate passed 3/3, and the following design cohort then
passed its treatment gate: Map7/Map9/Map10, Full/Sector/Adaptive, n=3,
27/27 valid spawn events, all requiring and observing exactly three
consecutive qualifying samples.  All 27 missions completed with zero source
or synthetic-cylinder contacts.  These rows are design data only.

The preregistered selector found 13 eligible 0.05 m lattice points and selected
the first lexicographic optimum:

- fixed world centre: `(22.50, 22.95)`;
- Sector proxy clearance: minimum 0.344687 m, median 0.500947 m;
- Adaptive proxy clearance: minimum 0.420500 m, median 0.597339 m;
- Full proxy clearance: minimum 0.146284 m, median 0.520011 m;
- conservative Map7/Map9/Map10 source gaps: 0.500895/0.788077/0.719521 m.

The positive Sector proxy means this frozen location is expected to be an
angular blind-zone exposure but is not preclaimed to force a Sector contact.
The centre will not be moved closer after viewing v6 outcomes.

Pre-flight reproducibility identifiers are:

- normalized common v6 profile SHA-256:
  `81b50081dd7e8e04ee0dd805c7cba48b79f9ad389ea3e24ccb48a3937a5abc71`;
- simulator header SHA-256:
  `60dcb0658940fe093b53e0c1f8b6123cd558bcac3755240480c8ee201adda275`;
- selector SHA-256:
  `8bda93b4b56d1a78823cedccb1fd63306541dd919f71b481d717eee6e7ef9aa7`;
- selection record SHA-256:
  `bc6656f18fc26a8f67601053b10ea01e42cf8d6939f947d1c6d4b8ba50966061`.

The evidence files are
`results/side_entry_v5_design_maps7_9_10_three_mode_n3_raw_20260907.csv` and
`results/side_entry_v6_center_selection_20260907.json`.  V6 first receives a
Map7 three-mode n=1 integration gate.  Only 3/3 validated events permit the
frozen rotating Map7/Map9/Map10 three-mode n=3 confirmatory cohort.  All
launched rows, contacts and infrastructure retries are retained.
