# Guarded v7 `full` / `sector` / `adaptive` seed1-10 × n=5

Date: 2026-08-20

## Result first

The 150 planned runs completed. Observed completion was `full` 48/50 (96%),
`sector` 46/50 (92%), and `adaptive` 47/50 (94%). The completion differences
were not distinguishable at this sample size: paired exact McNemar was
`p=0.6875` for full-sector and `p=1.0` for full-adaptive.

The filters did not deliver the intended large reduction. Weighted point
reduction was only 2.72% for sector and 2.54% for adaptive. ROG mapping total
time fell about 6.4%, but mean mission time increased about 4.1%. The reason is
visible in the filter telemetry: the replan-failure safety valve forced the
filter full-open for 91.5% of frames. This is a result for the current
canonical safety-valve modes, not for a strict always-closed ±60-degree sector
ablation.

The campaign's requested static-PCD option was not actually active. The runner
placed `--static-pcd` after argparse's `--` positional delimiter, so the
monitor ignored it. Completion, waypoint, mission-time, filter, mapping, CPU,
and live-cloud fields remain measured; every `static_pcd_*` zero/null in the
raw CSV is invalid as a safety measurement. The runner was fixed after the
campaign and now requires `static_pcd_enabled=true` plus a positive point
count, but this does not retroactively validate the 150 runs. A separate
post-fix seed1 full smoke completed 5/5 waypoints in 57.42 s with
`run_valid=true`, `static_pcd_enabled=true`, 241,490 loaded points, and zero
static marker. It validates the repaired launch path only and is not included
in any n=5 result.

## Protocol

- Maps: `seed1` through `seed10`
- Modes: `full`, `sector`, `adaptive`; five runs per seed and mode
- Total: 10 × 3 × 5 = 150 fresh-process runs
- Mission: `loop24.txt`, v=7, 120 s timeout, five waypoints
- Mode order: rotated each run to reduce fixed order effects
- Planner profile:
  `static_seedmaps_guard_viability_tight_v7_filtered.yaml`
- Planner/guard code was identical between modes. The new profile differs
  from `static_seedmaps_guard_viability_tight_v7.yaml` only by routing ROG-Map
  input from `/cloud_registered` through `/cloud_sector`.
- `full`: filter process is a 100% passthrough.
- `sector`: body-yaw ±60 degrees.
- `adaptive`: velocity-yaw ±60 degrees plus the existing stall opening logic.
- Both filtered modes retained the canonical replan safety valve: five
  consecutive `/planning/replan_status=false` messages open the filter and 15
  consecutive successes close it.
- Raw-cloud CIRI shadow remained off. No shadow result affected flight.

Command:

```bash
python3 scripts/native_campaign/native_campaign.py \
  --maps seed1 seed2 seed3 seed4 seed5 seed6 seed7 seed8 seed9 seed10 \
  --modes full sector adaptive --runs 5 --rotate-modes \
  --seedmap-super-config static_seedmaps_guard_viability_tight_v7_filtered.yaml \
  --seedmap-static-pcd --loop-timeout 120 \
  --artifacts-dir /tmp/guarded_3mode_n5_20260820_artifacts \
  --out /tmp/guarded_3mode_n5_20260820.csv
```

The command line documents intent, but the static-PCD option bug described
above invalidates only that auxiliary measurement.

## Completion by seed

Each completion cell is completed runs out of five. Waypoint totals are shown
where a mode failed.

| seed | full | sector | adaptive | live-cloud marker runs (F/S/A) |
|---:|:---:|:---:|:---:|:---:|
| 1 | 5/5 | 5/5 | 5/5 | 0 / 0 / 0 |
| 2 | 5/5 | 5/5 | 5/5 | 0 / 0 / 0 |
| 3 | 5/5 | 5/5 | 5/5 | 0 / 0 / 0 |
| 4 | 5/5 | 4/5 (23/25 WP) | 5/5 | 0 / 0 / 0 |
| 5 | 5/5 | 5/5 | 5/5 | 0 / 0 / 0 |
| 6 | 5/5 | 5/5 | 5/5 | 0 / 0 / 0 |
| 7 | 5/5 | 5/5 | 5/5 | 0 / 0 / 0 |
| 8 | 5/5 | 5/5 | 5/5 | 0 / 0 / 0 |
| 9 | 4/5 (24/25 WP) | 3/5 (17/25 WP) | 2/5 (18/25 WP) | 0 / 1 / 1 |
| 10 | 4/5 (21/25 WP) | 4/5 (21/25 WP) | 5/5 | 0 / 0 / 0 |
| **total** | **48/50 (245/250 WP)** | **46/50 (236/250 WP)** | **47/50 (243/250 WP)** | **0 / 1 / 1** |

The two live-cloud markers occurred in seed9 run2 adaptive and seed9 run3
sector at reported centre-to-point distances of 0.193 m and 0.163 m. The live
cloud is mode-dependent, so it is not a common cross-mode ground truth. It
also cannot be dismissed: the intended common static-PCD check was inactive.
Do not call this campaign zero-contact or safety-certified. In addition, the
0.20 m marker radius equals `robot_r`; it provides no positive clearance
margin even when correctly measured.

## Per-seed point reduction and mission time

Point reduction is `1 - sum(kept points) / sum(input points)` within each
mode. Times are five-run means and include 120 s failures.

| seed | sector points ↓ | adaptive points ↓ | mean time full / sector / adaptive (s) |
|---:|---:|---:|:---:|
| 1 | 4.25% | 4.70% | 64.28 / 62.20 / 65.90 |
| 2 | 5.52% | 5.34% | 62.86 / 60.24 / 55.60 |
| 3 | 3.79% | 4.50% | 61.74 / 70.81 / 67.53 |
| 4 | 3.37% | 3.08% | 71.87 / 81.45 / 74.14 |
| 5 | 4.13% | 4.24% | 65.96 / 74.89 / 70.38 |
| 6 | 3.10% | 2.91% | 78.21 / 77.96 / 87.57 |
| 7 | 2.16% | 1.90% | 87.28 / 92.81 / 91.58 |
| 8 | 1.95% | 1.92% | 89.29 / 81.20 / 79.26 |
| 9 | 1.01% | 1.01% | 94.02 / 107.95 / 117.47 |
| 10 | 2.68% | 1.51% | 98.83 / 96.37 / 96.19 |

The point reduction falls as maps become harder because the safety valve is
open more often: mean replan-guard open duty grows from roughly 87-90% on
seed1-2 to 93-96% on seed7-10.

## Aggregate reduction relative to full

Positive reduction means a lower value than full. Mission time uses “change”
instead, so positive values mean slower. Mapping metrics are means of the
per-run ROG performance summaries.

| metric | full | sector | adaptive |
|:---|---:|---:|---:|
| completion | 48/50 (96%) | 46/50 (92%) | 47/50 (94%) |
| failure rate | 4% | 8% (+4 pp; +100% relative) | 6% (+2 pp; +50% relative) |
| mean mission time | 77.43 s | 80.59 s (**+4.07%**) | 80.56 s (**+4.04%**) |
| weighted point reduction | 0% | **2.72%** | **2.54%** |
| mean replan full-open duty | 0% | **91.48%** | **91.54%** |
| mapping total time | 141.72 ms | 132.58 ms (**6.44% ↓**) | 132.70 ms (**6.36% ↓**) |
| raycast time | 85.77 ms | 80.54 ms (**6.10% ↓**) | 80.41 ms (**6.24% ↓**) |
| update time | 55.95 ms | 52.04 ms (**6.98% ↓**) | 52.29 ms (**6.55% ↓**) |
| mean FSM CPU | 144.88% | 140.23% (**3.21% ↓**) | 137.67% (**4.97% ↓**) |
| static-PCD contact | **not measured** | **not measured** | **not measured** |
| live-cloud marker runs | 0/50 | 1/50 | 1/50 |

The mean paired per-seed/run changes lead to the same qualitative result:
mission time changed by +5.25% for sector and +4.64% for adaptive, while
mapping total time fell 6.35% and 6.17%, respectively.

## Failures

| seed/run | mode | waypoint | path (m) | kept | replan-open duty |
|:---|:---:|:---:|---:|---:|---:|
| seed4/run3 | sector | 3/5 | 157.907 | 98.321% | 93.121% |
| seed9/run1 | sector | 2/5 | 110.026 | 99.036% | 97.205% |
| seed9/run2 | adaptive | 2/5 | 105.602 | 98.682% | 96.243% |
| seed9/run3 | sector | 0/5 | 12.235 | 99.443% | 97.149% |
| seed9/run4 | full | 4/5 | 208.288 | 100.000% | 0% |
| seed9/run4 | adaptive | 4/5 | 216.546 | 99.046% | 96.746% |
| seed9/run5 | adaptive | 2/5 | 152.509 | 98.653% | 95.021% |
| seed10/run2 | full | 1/5 | 44.469 | 100.000% | 0% |
| seed10/run5 | sector | 1/5 | 102.597 | 97.624% | 95.380% |

These failures do not support “the sector removed too many points” as the
primary explanation. Every filtered failure kept at least 97.6% of input
points and spent at least 93.1% of frames full-open. Full also failed once on
seed9 and once on seed10. The current guarded planner remains stochastically
unstable near the 120 s boundary; seed9 is the clearest stress case.

## Interpretation and next experiment

1. The present safety valve is too eager for an efficiency experiment. About
   68% of reported replans fail, which opens the filter almost continuously.
2. Keeping that valve is reasonable for this canonical safety-oriented mode,
   but it makes `sector`/`adaptive` poor labels for a strict field-of-view
   ablation. The observed 2.5-2.7% point reduction is the honest result for
   these modes.
3. A separate strict-sector ablation should use `--no-replan-guard`; it must
   not silently replace the canonical result. Run it only after the fixed
   static-PCD monitor is verified in the full launched stack.
4. The intended safety rerun remains outstanding. A future campaign must show
   nonzero `static_pcd_point_count` on every row before any contact or
   clearance claim is accepted.

## Artifacts

- Raw 150-run CSV:
  `results/guarded_v7_full_sector_adaptive_seed1_10_n5_20260820.csv`
- Derived 33-row summary:
  `results/guarded_v7_full_sector_adaptive_seed1_10_n5_summary_20260820.csv`
- Nine timeout monitor JSONs:
  `results/guarded_v7_full_sector_adaptive_seed1_10_n5_failures_20260820/`
- Full 300 run artifacts remain in
  `/tmp/guarded_3mode_n5_20260820_artifacts/` (58 MB).
