# Paired half-angle operating-envelope screen (2026-09-02)

## 1. Question and decision rule

The current +/-60 degree Sector condition completed safely as often as Adaptive
in the preceding Map1--10 campaign. This screen asks whether a narrower common
nominal half-angle on the same difficult maps exposes a loss that Adaptive's
temporary Full openings recover.

The three conditions were fixed before running the screen:

- 60 degrees: existing reference condition;
- 45 degrees: moderate angular-loss stress;
- 30 degrees: strong angular-loss stress.

The primary discriminator is a paired Sector-only completion failure or static-
PCD contact while Adaptive remains complete and contact-free. Mission time,
clearance, data rate, computation and transitions are secondary descriptive
signals. The screen uses only three repeats per map and is not a significance
test or a population guarantee. The `clearance < 0.20 m` count below is a
descriptive low-margin threshold, not a collision label or certified safety
boundary.

## 2. Implementation

`native_campaign.py` now accepts `--filter-half-angle-deg`, validates the value
in `[0, 180]`, and forwards the same value to the Sector and Adaptive native
front end in external, integrated and sensor-front-end backends. Its default is
60 degrees, so existing commands retain their behavior.

An independent, default-off OOM diagnostic was added with
`--optimizer-phase-memory-trace`. The runner exports
`SUPER_OPTIMIZER_PHASE_MEMORY_TRACE=1` only when requested. ExpTrajOpt and
BackupTrajOpt then emit begin/end markers around `lbfgs_optimize`, including
call number, duration, iterations, process `VmRSS`, `VmSwap` and RSS delta. A
process killed inside the optimizer leaves an unmatched begin marker. The
runner aggregates every attempt, including a failed attempt followed by a
successful retry, and reports the incomplete phase in the raw CSV.

The trace reads `/proc/self/status` only when enabled. It is off in normal use;
no standard `tight_v7` profile was changed. Because this experiment deliberately
enabled verbose per-call logging, its absolute time/CPU values should be used
for within-campaign comparisons, not substituted for earlier trace-off final
performance results.

## 3. Verification and protocol

Verification before the screen:

- Python compile and eight campaign parser tests passed;
- Release build of `super_planner` and `mission_planner` passed;
- Map1, 45 degrees, Sector/Adaptive one-run gate completed 2/2 with zero
  collision, no retry and no unmatched optimizer marker;
- the gate recorded Exp begin/end 401/401 and 381/381, and Backup begin/end
  660/660 and 630/630 for Sector and Adaptive respectively.

The screen ran Map7, Map9 and Map10, Sector and Adaptive, three times at each
angle: 3 angles x 3 maps x 2 modes x 3 repeats = 54 rows. Mode order rotated.
Both modes used the same angle. Static source-PCD collision checking, strict-
burst filtering, the C++ sensor front end, reliable filtered map delivery, 5 Hz
Adaptive cloud/risk caps and cgroup CPU accounting matched the preceding final
profile. The standard Full profile was supplied to the runner but Full was not
one of the executed modes.

Command template (replace `ANGLE` and output names):

```bash
python3 scripts/native_campaign/native_campaign.py \
  --maps seed7 seed9 seed10 --modes sector adaptive --runs 3 --rotate-modes \
  --seedmap-full-super-config static_seedmaps_guard_viability_tight_v7.yaml \
  --seedmap-filtered-super-config static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml \
  --seedmap-adaptive-super-config static_seedmaps_guard_viability_tight_v7_frontend_risk_enforce.yaml \
  --seedmap-static-pcd --loop-timeout 180 --filter-profile strict-burst \
  --filter-backend cpp-frontend --filter-half-angle-deg ANGLE \
  --filtered-reliable-map-link --adaptive-max-publish-hz 5 \
  --adaptive-risk-max-eval-hz 5 --adaptive-risk-body-clearance-m 0.20 \
  --adaptive-risk-body-horizon-s 0.15 \
  --adaptive-risk-body-max-odom-age-s 0.20 --cgroup-cpu-accounting \
  --optimizer-phase-memory-trace --artifacts-dir ARTIFACTS --out RAW.csv
```

## 4. Primary and aggregate results

All 54 rows completed on their first attempt, had zero static-PCD collision,
zero speed invalidation, zero OOM kill and zero optimizer phase mismatch.

| Half-angle | Mode | Complete | Collision runs | Mean time (s) | Mean/min clearance (m) | `<0.20 m` | Kept (%) | DDS (MiB/s) | Algorithm cores | Algorithm core-s | End-to-end core-s |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 60 | Sector | 9/9 | 0 | 73.280 | 0.256 / 0.211 | 0 | 55.430 | 4.536 | 1.034 | 78.226 | 96.058 |
| 60 | Adaptive | 9/9 | 0 | 71.323 | 0.258 / 0.219 | 0 | 40.364 | 3.364 | 1.070 | 78.716 | 99.876 |
| 45 | Sector | 9/9 | 0 | 76.611 | 0.242 / 0.173 | 2 | 50.529 | 4.145 | 1.003 | 79.166 | 97.782 |
| 45 | Adaptive | 9/9 | 0 | 72.436 | 0.249 / 0.226 | 0 | 39.447 | 3.262 | 1.039 | 77.147 | 98.747 |
| 30 | Sector | 9/9 | 0 | 73.750 | 0.243 / 0.186 | 2 | 44.522 | 3.623 | 0.977 | 74.052 | 91.620 |
| 30 | Adaptive | 9/9 | 0 | 70.831 | 0.254 / 0.226 | 0 | 36.880 | 3.074 | 1.037 | 75.809 | 97.354 |

Adaptive relative to same-angle Sector:

| Half-angle | Time reduction | Kept-point reduction | DDS reduction | Algorithm mean-core reduction | Algorithm core-s reduction | End-to-end core-s reduction | Min-clearance delta |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 60 | 2.670% | 27.180% | 25.852% | -3.444% | -0.626% | -3.975% | +0.008 m |
| 45 | 5.450% | 21.934% | 21.313% | -3.521% | +2.551% | -0.987% | +0.053 m |
| 30 | 3.958% | 17.163% | 15.133% | -6.137% | -2.372% | -6.259% | +0.040 m |

Positive reduction means Adaptive used less. Negative CPU reductions mean it
used more. Adaptive consistently reduced the measured DDS rate but did not
consistently reduce CPU work relative to Sector. This comparison also does not
replace the existing Full-versus-Adaptive result because Full was not rerun.

## 5. Map-labelled results and Adaptive transitions

Transition columns are totals across three Adaptive runs. `Open` is the main
adaptive recovery state, `TG` is a trajectory-guard edge and `EffFull` is the
combined effective-Full state edge. These counters overlap and must not be
summed into a single number of unique recovery episodes.

| Angle | Map | Mode | Complete/collision | Mean time (s) | Min clearance (m) | `<0.20 m` | DDS (MiB/s) | Algorithm cores | Open / TG / EffFull |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 60 | Map7 | Sector | 3/3 / 0 | 69.580 | 0.243 | 0 | 4.124 | 1.030 | 0 / 0 / 0 |
| 60 | Map7 | Adaptive | 3/3 / 0 | 68.887 | 0.264 | 0 | 3.101 | 1.079 | 1 / 19 / 55 |
| 60 | Map9 | Sector | 3/3 / 0 | 74.440 | 0.270 | 0 | 4.716 | 1.031 | 0 / 0 / 0 |
| 60 | Map9 | Adaptive | 3/3 / 0 | 73.863 | 0.245 | 0 | 3.572 | 1.048 | 3 / 20 / 65 |
| 60 | Map10 | Sector | 3/3 / 0 | 75.820 | 0.211 | 0 | 4.769 | 1.042 | 0 / 0 / 0 |
| 60 | Map10 | Adaptive | 3/3 / 0 | 71.220 | 0.219 | 0 | 3.418 | 1.082 | 1 / 16 / 49 |
| 45 | Map7 | Sector | 3/3 / 0 | 70.897 | 0.221 | 0 | 3.725 | 1.010 | 0 / 0 / 0 |
| 45 | Map7 | Adaptive | 3/3 / 0 | 70.087 | 0.228 | 0 | 3.035 | 1.047 | 1 / 15 / 67 |
| 45 | Map9 | Sector | 3/3 / 0 | 80.860 | 0.173 | 1 | 4.462 | 0.991 | 0 / 0 / 0 |
| 45 | Map9 | Adaptive | 3/3 / 0 | 72.670 | 0.226 | 0 | 3.494 | 1.031 | 1 / 19 / 67 |
| 45 | Map10 | Sector | 3/3 / 0 | 78.077 | 0.182 | 1 | 4.249 | 1.009 | 0 / 0 / 0 |
| 45 | Map10 | Adaptive | 3/3 / 0 | 74.550 | 0.235 | 0 | 3.256 | 1.038 | 0 / 20 / 44 |
| 30 | Map7 | Sector | 3/3 / 0 | 68.223 | 0.186 | 1 | 3.302 | 1.006 | 0 / 0 / 0 |
| 30 | Map7 | Adaptive | 3/3 / 0 | 65.730 | 0.226 | 0 | 2.701 | 1.041 | 1 / 17 / 50 |
| 30 | Map9 | Sector | 3/3 / 0 | 75.610 | 0.216 | 0 | 3.877 | 0.967 | 0 / 0 / 0 |
| 30 | Map9 | Adaptive | 3/3 / 0 | 71.713 | 0.238 | 0 | 3.259 | 1.027 | 1 / 21 / 58 |
| 30 | Map10 | Sector | 3/3 / 0 | 77.417 | 0.199 | 1 | 3.689 | 0.958 | 0 / 0 / 0 |
| 30 | Map10 | Adaptive | 3/3 / 0 | 75.050 | 0.226 | 0 | 3.263 | 1.043 | 2 / 14 / 49 |

Across the nine Adaptive rows at 60/45/30 degrees, main opens totaled 5/2/4,
trajectory-guard opens 55/54/52 and effective-Full opens 169/178/157. One
natural current-body brake occurred at 30 degrees on Map9; active-brake
replacement was zero. The deterministic replacement gate from the preceding
stage remains its coverage evidence.

## 6. OOM phase evidence

The host swap was already nearly full throughout this campaign, but no run was
killed and every phase marker closed:

- ExpTrajOpt begin/end: 23,847 / 23,847;
- BackupTrajOpt begin/end: 41,100 / 41,100;
- maximum optimizer-observed process RSS: 3,282.7 MiB;
- maximum end-to-end sampled RSS: 3,723.9 MiB;
- maximum whole-benchmark cgroup memory: 9,597.2 MiB;
- maximum single-call RSS delta: Exp 7.766 MiB, Backup 8.871 MiB;
- maximum single-call duration: Exp 803.407 ms, Backup 944.891 ms;
- cgroup OOM-kill delta: zero for all 54 rows.

The long optimizer calls show a latency tail, but they did not coincide with a
large per-call RSS jump in this sample. This does not clear the optimizer or
explain the earlier Map6 OOM: Map6 was not in this reduced screen, only 54 rows
were run, and the prior failure may depend on cumulative host co-tenancy and
transient FSM growth. The useful result is that a future recurrence will now
identify whether the process died inside Exp, inside Backup, or outside both.

## 7. Decision

No tested half-angle is a primary completion/contact discriminator. Sector and
Adaptive were both 27/27 complete and collision-free across all angles. There
were no discordant primary pairs, so no McNemar test was performed. Even 9/9 at
one angle has a Wilson 95% lower bound of only about 70.1%, not a 100%
population guarantee.

The 45-degree condition is the most informative secondary stress point: Sector
had two low-clearance rows, Adaptive had none, Adaptive's worst clearance was
0.053 m higher, mean time was 5.450% lower and DDS was 21.313% lower. However,
that is a descriptive margin/time result, not proof that Adaptive improves
completion or collision rate. Selecting 45 degrees and then describing it as a
demonstrated safety win would overstate the evidence.

The next defensible step is not further post-hoc angle tuning on these same
maps. If a safety-ablation contribution is required, change a pre-declared
topological property of the experiment (for example a side-entry/turning
occluder placement or a fixed sensor-latency envelope), freeze it independently
of outcomes, and then run paired Sector/Adaptive trials. If the paper scope can
be narrower, retain +/-60 degrees and claim the already measured communication
reduction plus equal observed safety in this benchmark, without claiming an
Adaptive safety-rate advantage.

## 8. Evidence

- Raw CSVs:
  `results/half_angle_sweep_a{60,45,30}_maps7_9_10_sector_adaptive_n3_raw_20260902.csv`
- Aggregate:
  `results/half_angle_sweep_maps7_9_10_sector_adaptive_n3_summary_20260902.csv`
- Adaptive-versus-Sector reductions:
  `results/half_angle_sweep_maps7_9_10_sector_adaptive_n3_reductions_20260902.csv`
- Functional gate:
  `results/half_angle_phase_gate_map1_n1_raw_20260902.csv`

The large per-run artifact directories remain local. They contain phase logs,
memory/cgroup traces and filter statistics and are intentionally not required
for the compact repository evidence set.
