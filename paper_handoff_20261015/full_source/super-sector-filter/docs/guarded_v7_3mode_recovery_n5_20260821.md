# Guarded v7 full/sector/adaptive paired n=5 campaign (2026-08-21)

## Scope and protocol

This campaign compares the current guarded-recovery build in `full`, `sector`,
and `adaptive` modes. Seeds 1-10 were each run five times per mode, with the
mode order rotated inside each seed/run block. All modes used the same v=7
planner profile, waypoint loop, timeout, sensor configuration, binary, and
static-PCD collision monitor.

```bash
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 scripts/native_campaign/native_campaign.py \
  --maps seed1 seed2 seed3 seed4 seed5 seed6 seed7 seed8 seed9 seed10 \
  --modes full sector adaptive --runs 5 --rotate-modes \
  --seedmap-super-config static_seedmaps_guard_viability_tight_v7_filtered.yaml \
  --seedmap-static-pcd --loop-timeout 140 \
  --artifacts-dir /tmp/guarded_3mode_recovery_n5_20260820_artifacts \
  --out /tmp/guarded_3mode_recovery_n5_20260820.csv
```

The campaign produced 150/150 valid rows, 150/150 forensic JSON files, and
150/150 stack logs. `static_pcd_enabled=true` in every row. The loaded point
counts were 241,490 for seeds 1/2, 444,850 for 3/4, 635,500 for 5/6, 838,860
for 7/8, and 1,042,220 for 9/10.

## Completion and per-seed results

Mission time below is the mean over all five runs, so a failed run contributes
the 140 s timeout. Map Hz is the achieved ROG-map commit cadence, not the
configured replan rate. Kept is the point-weighted direct filter output; full
is 100% by definition. Clearance is the worst static-PCD body clearance in the
five-run cell.

| seed | completion F/S/A | mean time F/S/A (s) | map Hz F/S/A | kept S/A | worst clearance F/S/A (m) |
|---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 5/5 / 5/5 / 5/5 | 60.59 / 60.83 / 63.07 | 6.13 / 6.51 / 6.40 | 94.89% / 95.79% | 0.206 / 0.251 / 0.227 |
| 2 | 5/5 / 5/5 / 5/5 | 56.80 / 57.50 / 59.24 | 6.31 / 6.70 / 6.23 | 95.06% / 95.81% | 0.244 / 0.232 / 0.266 |
| 3 | 4/5 / 5/5 / 5/5 | 80.63 / 64.28 / 71.87 | 4.39 / 4.22 / 3.58 | 94.82% / 95.03% | 0.285 / 0.283 / 0.246 |
| 4 | 5/5 / 5/5 / 5/5 | 80.18 / 72.79 / 74.79 | 3.37 / 3.92 / 3.85 | 96.24% / 97.20% | 0.212 / 0.235 / 0.266 |
| 5 | 5/5 / 5/5 / 5/5 | 70.01 / 72.02 / 71.57 | 3.50 / 3.59 / 3.52 | 96.11% / 95.31% | 0.181 / 0.109 / 0.209 |
| 6 | 4/5 / 5/5 / 5/5 | 93.96 / 76.35 / 77.03 | 3.21 / 3.50 / 3.54 | 97.02% / 96.44% | 0.247 / 0.199 / 0.150 |
| 7 | 4/5 / 5/5 / 5/5 | 93.16 / 90.83 / 92.01 | 3.14 / 3.09 / 2.87 | 97.99% / 97.39% | 0.211 / 0.150 / 0.179 |
| 8 | 5/5 / 5/5 / 5/5 | 76.38 / 77.53 / 75.50 | 3.11 / 3.16 / 3.38 | 97.46% / 97.44% | 0.222 / 0.238 / 0.079 |
| 9 | 4/5 / 4/5 / 5/5 | 105.62 / 101.69 / 84.70 | 3.44 / 3.05 / 3.35 | 98.08% / 97.89% | 0.210 / 0.230 / 0.210 |
| 10 | 5/5 / 5/5 / 5/5 | 96.48 / 87.36 / 85.87 | 2.81 / 3.60 / 3.64 | 97.89% / 98.28% | 0.129 / 0.211 / 0.217 |
| **total** | **46/50 / 49/50 / 50/50** | **81.38 / 76.12 / 75.57** | **3.94 / 4.13 / 4.04** | **97.03% / 96.99%** | **0.129 / 0.109 / 0.079** |

The observed completion rates are full 92%, sector 98%, and adaptive 100%.
The paired differences are not statistically established at this sample size:
exact two-sided McNemar gives full-versus-sector `p=0.375`
(one full-only and four sector-only completions), full-versus-adaptive
`p=0.125` (zero full-only and four adaptive-only), and
sector-versus-adaptive `p=1.0` (zero sector-only and one adaptive-only).

## Frequency and processing differences

The configured frequencies did not vary by mode:

| configured item | all three modes |
|---|---:|
| LiDAR sensing target | 10 Hz |
| planner replan target | 15 Hz |
| main FSM wall timer | 100 Hz |
| command publication wall timer | 100 Hz |

The achieved rates and per-update costs did vary:

| metric | full | sector | adaptive | sector vs full | adaptive vs full |
|---|---:|---:|---:|---:|---:|
| completion | 92% | 98% | 100% | +6 pp | +8 pp |
| mean mission, all runs | 81.38 s | 76.12 s | 75.57 s | -6.47% | -7.15% |
| mean mission, successes only | 76.28 s | 74.81 s | 75.57 s | -1.93% | -0.94% |
| cloud callback rate | 6.51 Hz | 6.82 Hz | 6.63 Hz | +4.75% | +1.84% |
| map commit rate | 3.94 Hz | 4.13 Hz | 4.04 Hz | +4.93% | +2.47% |
| mean scan points | 28,645 | 28,103 | 28,167 | -1.89% | -1.67% |
| direct point reduction | 0% | 2.97% | 3.01% | +2.97 pp | +3.01 pp |
| ROG processed points | 102.78 kpoint/s | 106.17 kpoint/s | 105.32 kpoint/s | +3.30% | +2.48% |
| mapping total/update | 131.65 ms | 124.97 ms | 125.29 ms | -5.07% | -4.83% |
| raycast/update | 79.00 ms | 75.04 ms | 75.17 ms | -5.02% | -4.85% |
| update/update | 52.64 ms | 49.93 ms | 50.11 ms | -5.15% | -4.81% |
| FSM CPU | 126.34% | 126.60% | 125.16% | +0.21% | -0.94% |
| filter/observer CPU | 10.56% | 11.11% | 11.25% | +0.55 pp | +0.68 pp |

The filter was open 90.96% of wall time in sector and 90.79% in adaptive;
point-weighted open duty was 94.44% and 94.23%. Consequently it removed only
about 3% of points. That small reduction still lowered mean per-map work by
about 5% and raised aggregate achieved map cadence by 2.5-4.9%. The effect is
not universal: seed4 and seed10 improved clearly, while seed5 was neutral to
slightly slower and seed7's achieved cadence fell in both filtered modes.

The all-run mission-time improvement is inflated by full's four 140 s
timeouts. Success-only means differ by only 0.9-1.9%. The nominal 10 Hz LiDAR
target was not achieved in any mode; observed cloud callback rates were
65.1%, 68.2%, and 66.3% of that target. For full, the full-open filter observer
counts the raw stream but is not inserted into the planner's input path.

## Failure and recovery-path inspection

| failed run | progress | dominant observed failure | relevant markers |
|---|---:|---|---|
| seed3 run4 full | 2/5 | repeated MINCO/EXP generation failure | MINCO 6,495; GenerateExp failure 6,495; reroute arm 1; no `NO_PATH` |
| seed6 run5 full | 2/5 | repeated MINCO/EXP generation failure | MINCO 6,371; GenerateExp failure 6,356; reroute arm 1; no `NO_PATH` |
| seed7 run4 full | 1/5 | repeated corridor/polytope construction failure | polytope path/line 2,986/2,988; reroute arm 2; backup fallback 1; no `NO_PATH` |
| seed9 run3 full | 0/5 | repeated MINCO/EXP generation failure | MINCO 11,460; GenerateExp failure 11,462; reroute arm 1; backup fallback 1; no `NO_PATH` |
| seed9 run1 sector | 4/5 | repeated topology churn near the last waypoint | reroute arm 38; guard reject 91; `NO_PATH` 27; epoch reset 9 |

Across all 150 runs, backup-fallback markers were full/sector/adaptive
33/38/29, reroute-arm markers were 284/312/274, and epoch resets were 1/10/1.
No direct-goal fallback commit or rejection marker appeared in any run. Thus
the bounded direct-goal branch added in section 8.15 was not exercised; its
preconditions did not cover these residual failures.

## Safety and instrumentation caveats

- Static-PCD collisions were 0/50 in every mode. Worst positive body
  clearances were 0.129 m full, 0.109 m sector, and 0.079 m adaptive.
- The live-cloud monitor emitted one marker in seed5 run2 sector at 0.196 m,
  but the mode-independent static PCD measured 0.309 m centre distance and
  +0.109 m body clearance at its closest point, with zero static collision.
  This is retained as a live-cloud-only marker rather than counted as a
  static-ground-truth contact.
- A null static minimum means no reference point entered the monitor's exact
  0.5 m search radius during that run; it implies body clearance greater than
  0.3 m, not a failed static query. Each seed/mode cell had at least one exact
  value, so the cell-wise worst clearances above are defined.
- Three observer rows reported first open/close timestamps in reverse order.
  This is a first-transition diagnostic ordering issue and does not affect the
  filter's own accumulated open-duty counters used above.
- Raw-cloud CIRI remains shadow-only and default false; it was not enabled in
  the tested practical profile and did not affect flight decisions.

## Conclusion

Adaptive is the best completion result in this one paired cohort, but 50/50 is
not a proof of deterministic completion and its worst measured clearance is
the smallest of the three modes. Sector and adaptive reduce direct point load
only about 3%; the main measurable benefit is approximately 5% lower mapping
work per committed update. The current recovery patch is therefore a material
improvement over the earlier deadlock, not a complete liveness solution: full
still failed four times and sector once, through at least two mechanisms not
covered by the direct-goal fallback.

Committed machine-readable outputs:

- `results/guarded_v7_3mode_recovery_n5_raw_20260821.csv`
- `results/guarded_v7_3mode_recovery_n5_summary_20260821.csv`
