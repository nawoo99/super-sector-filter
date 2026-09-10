# Static burst-dropout C4--C5 prospective extension preregistration

Date frozen: 2026-09-10 (Asia/Seoul), before C4/C5 asset generation, replay,
gate flight, or campaign outcome

Status at freeze: **prospective extension; no C4/C5 outcome observed**

Outcome addendum (added only after all frozen flights completed): all
structure, paired production replay and one-row Full feasibility gates passed.
The exact 120-row matrix contained only unique first attempts and passed every
dropout, speed, resource, static-PCD and OOM integrity check. Full and Adaptive
were each 40/40 safe; Fixed Sector was 7/40 safe with 32 contact rows and four
non-completions. Paired discordance was 33:0, exact two-sided McNemar
p=`2.3283064365386963e-10`, so the frozen decision is
**`C4_C5_EXTENSION_OBSERVED`**. Details are in
`docs/ten_condition_n20_result_20260910.md`.

## Purpose and claim boundary

The completed paper table contains five normal radius tiers and three static
burst-dropout stress maps. This extension adds two new static blind-fork
geometries so the stress family contains five physical maps, C1--C5. Existing
C1--C3 rows, maps and decisions remain immutable.

Because C4/C5 were designed after C1--C3 results were known, this is a
prospective extension/replication, not a rewrite of the original held-out
confirmation. C4 and C5 must be reported even if either fails a gate or does
not reproduce the prior ordering. No post-outcome geometry or policy tuning is
allowed.

SUPER, v7 dynamics, Full/Sector/Adaptive implementations, the fixed 45-degree
Sector, 1.5 m omnidirectional near-field bubble, Adaptive thresholds, mission,
contact radius, 7 m/s speed limit, resource gates and the 10 Hz burst-dropout
contract are frozen at mirror commit
`17693525ebd360230d4fcabaa3247bf759897339`.

## Frozen common sensor and mission contract

- start `(24.5, 0.0, 1.5)`, single target `(24.5, 20.0)` via
  `blind_heading_fork.txt`;
- renderer 10 Hz, 15 m horizon, 360-degree raw LiDAR;
- 1.0 s delivered warm-up followed by recurrent 0.5 s output suppression
  every 2.0 s;
- paired run phase `0.2 * ((run - 1) mod 10)` for runs 1--20;
- rendering and dynamics continue during loss;
- the common injector acts before DDS/direct Full/direct C++ frontend paths;
- obstacle height 3.2 m, wall thickness 0.3 m, body/contact radius 0.2 m.

## Frozen geometry C4: `shc4_deep_mirror`

C4 is a deeper mirrored fork with a longer divider and a wider east bypass:

- outer walls x=20.75 and x=29.25, y=-3..23;
- divider x=26.0, y=1.5..16.5;
- west-branch closure `(20.90,5.0)` to `(26.0,5.0)`;
- initial body yaw 0 degrees (east), velocity direction north;
- east bypass anchors `(24.5,0) -> (27.5,1) -> (27.5,17.0) -> (24.5,20)`;
- direct route x=24.5 must body-intersect the closure;
- replay trajectory `(24.5,0,1.5) -> (24.5,6.0,1.5)` in 1.0 s;
- hazard audit centre `(24.3,5.0)`, radius 1.1 m.

## Frozen geometry C5: `shc5_asymmetric_offset`

C5 is an unmirrored asymmetric-width fork with a shorter offset divider:

- outer walls x=19.75 and x=28.75, y=-3..23;
- divider x=22.9, y=2.0..13.75;
- east-branch closure `(22.9,4.75)` to `(28.60,4.75)`;
- initial body yaw 180 degrees (west), velocity direction north;
- west bypass anchors `(24.5,0) -> (21.15,1) -> (21.15,14.75) -> (24.5,20)`;
- direct route x=24.5 must body-intersect the closure;
- replay trajectory `(24.5,0,1.5) -> (24.5,5.75,1.5)` in 1.0 s;
- hazard audit centre `(25.0,4.75)`, radius 1.0 m.

Each condition has a clear control and hazard member differing only by its
registered closure. Names and dimensions cannot be substituted after a gate
or flight result.

## Frozen gates and execution order

For C4 then C5:

1. Generate the exact clear/hazard pair and record hashes.
2. Structure gate requires exact common background, positive closure delta,
   negative direct-route body clearance, the registered three-cell-inflated
   bypass, zero initial body-Sector closure samples and at least 20
   north-velocity-Sector closure samples.
3. Paired production replay feeds the same ten actual MARSIM frames to Sector
   and Adaptive and requires identical raw stream hashes, raw hazard/path
   conflict in at least two frames, zero Sector hazard/path leakage, and at
   least two consecutive fresh Adaptive `OCCUPIED` verdicts.
4. Exactly one separate Full feasibility row per hazard map must complete on
   its first attempt with zero static-PCD contact and valid dropout, speed,
   resource and OOM checks.
5. Only after both Full gates pass, run the fixed rotating-order matrix of
   20 new rows per map and mode. Gate rows are not pooled. Outcome replacement
   is forbidden; a retry remains an integrity failure even if retained by the
   runner.

A failed structure/replay/Full gate stops that map and is reported. It does
not authorize moving the closure or replacing the map.

## Frozen endpoints and decisions

Safe completion is mission completion with zero authoritative static-PCD
contact. Report C4 and C5 separately before aggregation.

`C4_C5_EXTENSION_OBSERVED` requires:

- both maps pass every prerequisite gate;
- an exact unique 120-row matrix, 20 rows per map and mode;
- all rows are first-attempt and pass phase/cadence, speed, resource,
  static-PCD and zero-OOM integrity;
- Full and Adaptive each achieve 20/20 safe completion on both maps;
- Fixed Sector is unsafe at least once on both maps; and
- across 40 paired Sector/Adaptive rows, discordance favours Adaptive and
  exact two-sided McNemar p<0.05.

If the matrix is valid and directionally favourable but any strict safety
criterion fails, report `C4_C5_EXTENSION_PARTIAL`. Gate, integrity, missing
matrix or non-favourable failures produce `C4_C5_EXTENSION_FAILED`.

The final ten-condition table is complete only with R1--R5, C1--C3 and C4--C5
each containing exactly 20 rows per mode: 600 rows total. C1--C3, C4--C5 and
C1--C5 aggregates are reported separately. The C1--C5 aggregate test is
secondary/descriptive because the extension was chosen after observing
C1--C3. Normal and stress time/CPU/bandwidth/safety rates are never pooled.
No 20/20 or larger all-success cell is a population-level 100% guarantee.

Frozen source hashes:

- normal CSV: `b40f880271a52f4b3332bfe67afe3d489cf8c6d444ac0c72ed30d9e9cd445ec5`;
- normal validation: `ea8091c1fac455e07e153e9034a4fef913563509ccb3db4c27ae2374fae7ae0a`;
- C1--C3 n=20 CSV: `7cc9bbaf238203bc8b9d0ec16dceb977a44fbb118dc41d5aabe7356cf30fad1a`;
- eight-condition result: `f6c20e1a5ef4dffc3c6306c3c3a5f8eec7fb24aadb8c7647dbcf306702706c80`.
