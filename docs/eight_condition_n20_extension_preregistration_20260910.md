# Eight-condition n=20 extension preregistration

Date frozen: 2026-09-10 (Asia/Seoul), before any C1--C3 replication-block
flight

Status: **frozen extension; block-2 outcomes not yet observed**

## Purpose and non-retrospective boundary

This extension produces a compact paper table with eight explicitly labelled
conditions and 20 observations per mode and condition. It does not delete or
rewrite the already observed Map1--10 or C1--C3 campaigns. The first five
conditions collapse the two deterministic random-layout replicates at each
pre-existing obstacle-radius tier; the final three conditions extend the
held-out burst-dropout maps with a separately reported replication block.

This is a reporting/replication extension after the original outcomes are
known. It is not a second claim that all 480 rows were prospectively hidden.
The original Map1--10 result and the preregistered C1--C3 block 1 retain their
own status and must remain traceable.

SUPER, v7 dynamics, Full/Sector/Adaptive implementations, the 45-degree fixed
Sector, 1.5 m omnidirectional near-field bubble, Adaptive thresholds, mission
files, fault schedule, contact radius, speed limit and resource gates are
frozen at mirror commit
`6981c94cff107d9fad49c853ac770e8031d786cf`. No planner or policy tuning is
allowed in this extension.

## Frozen eight conditions

### Normal-rate controlled size sweep

No new normal-map flights are required. Each condition contains both random
layout replicates and ten runs per layout, giving 20 rows per mode while
preserving layout variability:

| Condition | Physical maps | Cylinder radius | Rows per mode |
|---|---|---:|---:|
| R1 | `seed1`, `seed2` | 0.150 m | 2 layouts x 10 = 20 |
| R2 | `seed3`, `seed4` | 0.275 m | 2 layouts x 10 = 20 |
| R3 | `seed5`, `seed6` | 0.400 m | 2 layouts x 10 = 20 |
| R4 | `seed7`, `seed8` | 0.525 m | 2 layouts x 10 = 20 |
| R5 | `seed9`, `seed10` | 0.650 m | 2 layouts x 10 = 20 |

The frozen source is
`results/allmaps_stationary_conflict_deployed_resource_guard_three_mode_n10_raw_20260905.csv`
(SHA-256
`b40f880271a52f4b3332bfe67afe3d489cf8c6d444ac0c72ed30d9e9cd445ec5`).
Its frozen validation file has SHA-256
`ea8091c1fac455e07e153e9034a4fef913563509ccb3db4c27ae2374fae7ae0a`
and records 300/300 unique, quality-valid rows. These conditions use the
normal sensor profile and `loop24.txt` mission. They support normal-condition
completion, contact, CPU and bandwidth results.

### Static blind-fork burst-dropout stress

| Condition | Physical map | Existing block | New block | Final rows per mode |
|---|---|---:|---:|---:|
| C1 | `shc1_mirror_hazard` | runs 1--10 | runs 11--20 | 20 |
| C2 | `shc2_wide_offset_hazard` | runs 1--10 | runs 11--20 | 20 |
| C3 | `shc3_near_short_hazard` | runs 1--10 | runs 11--20 | 20 |

Block 1 is the already preregistered confirmation campaign
`results/static_burst_dropout_confirmation_three_mode_n10_raw_20260910.csv`
(SHA-256
`6176c0ed511fd0fb4972856fc308e10e89e79d84415cf6cf32c157cc1a203279`).
Its result JSON has SHA-256
`1be9a7d193a72f67e2cdbab519bc7b9724a7b07a458ff6ced1818e891bf12110`
and decision `CONFIRMATORY_TRANSFER_OBSERVED`.

Block 2 consists of exactly ten new rotating-order rows per map and mode.
Run indices 11--20 repeat the balanced phase grid independently:
`0.0, 0.2, ..., 1.8 s`, using
`phase = 0.2 * ((run - 1) mod 10)`. The renderer remains 10 Hz; after 1.0 s
warm-up, completed sensor output is suppressed for 0.5 s every 2.0 s before
all transport paths. Block-2 rows are never substituted for block-1 rows.

## Execution and integrity

The existing block-1 CSV is copied unchanged to a new n=20 result file. The
campaign runner uses `--runs 20 --resume-existing`, which must skip all 90
registered run-1--10 keys and append only the 90 run-11--20 keys. Mode order
continues to rotate by run index.

Every block-2 row must retain:

- unique `(map, run, mode)` key and run in 11--20;
- matching configured and observed dropout phase;
- 9.5--10.5 Hz rendered cadence, at least one burst, positive lost frames,
  maximum consecutive loss of 4--6 frames and delivered gap 0.45--0.75 s;
- valid speed, resource, static-PCD and run gates;
- first-attempt completion metadata and zero cgroup OOM kills.

An actual infrastructure failure may be retained by the runner, but any retry
makes the strict block-2 integrity endpoint fail; it is not silently replaced.
No geometry, fault, threshold, mode configuration or outcome criterion may be
changed after the first block-2 flight.

## Frozen analysis and decisions

Safe completion means mission completion with zero authoritative static-PCD
contact. Report each of R1--R5 and C1--C3 before group aggregates.

The C1--C3 block-2 replication decision is
`STRESS_REPLICATION_OBSERVED` only if:

- Full and Adaptive each achieve 10/10 safe completion on every C map;
- Fixed Sector has at least one unsafe paired row on every C map;
- across the 30 new paired Sector/Adaptive rows, discordance favours Adaptive
  and exact two-sided McNemar p < 0.05; and
- all 90 new rows pass the strict integrity rules.

Otherwise report `STRESS_REPLICATION_PARTIAL` or
`STRESS_REPLICATION_FAILED`; the original block-1 result is not erased and
the failed row is not rerun for outcome replacement.

The combined eight-condition table is complete only with exactly 20 rows per
mode and condition: 100 normal-rate rows per mode across R1--R5 and 60 stress
rows per mode across C1--C3, for 480 rows total. C1--C3 block 1, block 2 and
combined n=20 statistics are reported separately. The combined stress
McNemar test is secondary because the extension was chosen after block-1
outcomes.

Normal and stress conditions must not be pooled for mission time, CPU,
bandwidth or a single overall success rate. R1--R5 remain the primary
normal-condition efficiency evidence. C1--C3 remain a bounded static
burst-dropout safety-robustness result. No observed 20/20 cell is a
population-level 100% guarantee.

## Post-freeze outcome addendum

Added after all block-2 flights; the frozen specification above is unchanged.

The 90 new run-11--20 rows completed on unique first attempts with no retry,
infrastructure failure or OOM kill. All registered phase/cadence, speed,
resource, static-PCD and run-integrity checks passed. Full and Adaptive were
10/10 safe on each of C1--C3. Fixed Sector was safe 3/10, 5/10 and 6/10,
respectively, and therefore unsafe at least once on every map.

Block-2 paired discordance was 16 Sector-unsafe/Adaptive-safe versus zero in
the reverse direction; exact two-sided McNemar
p=`3.0517578125e-05`. The preregistered replication decision is therefore
`STRESS_REPLICATION_OBSERVED`. The complete eight-condition matrix contains
20 rows per mode and condition and receives decision
`EIGHT_CONDITION_N20_COMPLETE`.

The combined C1--C3 n=20 table is secondary: Full/Adaptive were each 60/60
safe, Sector was 27/60 safe, and paired discordance was 33:0 with
p=`2.3283064365386963e-10`. Normal and stress metrics remain separate. Full
tables, efficiency results, limitations and evidence hashes are recorded in
`docs/eight_condition_n20_result_20260910.md`.
