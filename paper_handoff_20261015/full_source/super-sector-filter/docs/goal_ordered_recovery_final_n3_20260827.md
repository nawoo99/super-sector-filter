# Goal-ordered bounded recovery and final three-mode n=3 regression

Date: 2026-08-27

Runtime workspace: `/root/super_ws/src/SUPER`

Mirror repository: `/root/super-sector-filter`

## Scope and decision

This iteration executed the four requested steps in order:

1. instrument the rare map8 Full topology-search tail;
2. bound the certified stop-and-reroute recovery without weakening its
   trajectory or stop-viability certificates;
3. regress maps7-10 in Full and Adaptive modes;
4. regress maps1-10 in Full, fixed-Sector and Adaptive modes.

The final implementation treats recovery budgets as belonging to a stopped
location episode. A short, certified escape commit clears pose-specific
blockers but no longer re-arms the same local/vertical recovery budget.
Budgets reset only for a new goal or after 2.0 m of horizontal progress. Local
escape now has eight horizontal alternatives, with the directions that make
the most progress toward the current waypoint tried first. Local and vertical
recovery are armed sequentially, so one event cannot consume both budgets.

The hard safety decision is unchanged: every escape or lift still goes through
the existing geometric trajectory guard and sampled stop-viability checks.
The raw-cloud CIRI feature remains default `false` and non-authoritative.

## Step 1: map8 Full tail instrumentation

The earlier independent n=5 campaign contained a direct long-tail example:
map8 Full run2 completed in 293.79 s after 154 topology arms and 363 searches.
The repeated sequence returned to the same stopped pocket after short commits.

A pre-change map8 Full n=10 reproduction completed 10/10, contact-free, with
mean/median/max times of 73.96/73.67/81.63 s. It did not reproduce the 293.79 s
tail; topology arm/search totals were 48/70. This confirms the failure is a
rare trajectory-dependent tail rather than deterministic for seed8.

Raw: `results/full_map8_prebound_n10_raw_20260827.csv`

## Step 2: bounded recovery implementation and counterexample

The first implementation preserved recovery budgets across short commits and
expanded local escape from four to eight directions. A default-off forced
branch test skipped the first candidate, committed candidate 2/8 through the
normal certificate, and completed map8 Adaptive in 68.11 s with zero contact.

The first post-change map8 Full n=10 also completed 10/10, contact-free, with
mean/median/max times of 72.76/71.49/92.31 s. One attempt was killed by the
host OOM killer and was retried once; the accepted retry completed in 71.64 s.
The failed process grew from roughly 3.0 GiB RSS to 9.1 GiB while host swap was
full. Other attempts stayed around 3.3-3.5 GiB, and the final 90-run campaign
had no OOM or retry. The anomalous allocation source is not yet localized, but
the evidence rejects batch accumulation and topology-counter explosion as its
immediate cause.

The first maps7-10 n=3 Full/Adaptive gate then found a useful counterexample:
23/24 completed, while map10 Adaptive run3 timed out at 300.01 s. The first
safe local step moved north-east even though the waypoint was west, and the
same recovery event consumed both the local and vertical budgets. It reached
121 arms, 357 searches and 116 epoch resets. Therefore the initial bound was
not accepted as the final fix.

The final correction goal-orders the eight candidates and makes local/vertical
arming mutually exclusive. A focused map10 Adaptive n=5 gate then completed
5/5 on the first attempt, contact-free, with mean/max 90.82/98.61 s, maximum
12 arms and 26 searches, and zero epoch-reset loop.

Raw evidence:

- `results/recovery_episode_8way_forced_seed8_adaptive_raw_20260827.csv`
- `results/full_map8_episode_bound_n10_raw_20260827.csv`
- `results/episode_bound_dense_full_adaptive_n3_raw_20260827.csv`
- `results/goal_ordered_seed10_adaptive_n5_raw_20260827.csv`

## Step 3: maps7-10 Full/Adaptive regression

The final binary completed all 24 requested runs on the first attempt. Every
run was contact-free, static-PCD collision-free and speed-valid.

| Map | Full complete/safe | Full mean / max (s) | Adaptive complete/safe | Adaptive mean / max (s) |
|---:|---:|---:|---:|---:|
| 7 | 3/3 | 77.69 / 84.28 | 3/3 | 73.41 / 81.12 |
| 8 | 3/3 | 69.79 / 72.98 | 3/3 | 82.64 / 86.79 |
| 9 | 3/3 | 84.59 / 92.19 | 3/3 | 84.64 / 87.80 |
| 10 | 3/3 | 88.91 / 91.73 | 3/3 | 88.56 / 97.08 |

Across these 12 matched runs per mode, Adaptive reduced points/update 15.40%,
map total/update 17.06%, occupancy update time 8.41% and FSM CPU 15.16% versus
Full. Mean mission time increased 2.58%. Adaptive opened full view 118 times.

Raw: `results/goal_ordered_dense_full_adaptive_n3_raw_20260827.csv`

## Step 4: maps1-10 final three-mode n=3 regression

All 90 rows completed on the first attempt; retry and OOM deltas were zero,
and all 90 were speed-valid. Safety-qualified means completed, live contact 0,
static-PCD collision 0 and speed-valid.

| Mode | Complete | Safety-qualified | Live contact runs/events | Static collision runs/events | Mean / median / max time (s) | Worst static clearance (m) |
|---|---:|---:|---:|---:|---:|---:|
| Full | 30/30 | 30/30 | 0 / 0 | 0 / 0 | 71.51 / 67.62 / 115.43 | +0.195 |
| Sector | 30/30 | 29/30 | 1 / 2 | 1 / 1 | 74.14 / 72.60 / 95.83 | -0.107 |
| Adaptive | 30/30 | 30/30 | 0 / 0 | 0 / 0 | 77.18 / 73.63 / 128.46 | +0.188 |

The fixed-Sector degradation was map9 run1: it completed but recorded two live
contact events, one static collision and -0.107 m clearance. Full and Adaptive
were contact-free on all maps in this cohort.

### Map-labelled result

`F/S/A` denotes Full/Sector/Adaptive. Times and computation are arithmetic
means across the three runs. Adaptive opens are the total effective full-view
open transitions across those runs.

| Map | Mode | Complete | Safe | Contact events | Mean / max time (s) | Min clearance (m) | Points/update | Total/update (ms) | Update (ms) | Effective update rate (Hz) | FSM CPU (%) | Adaptive opens |
|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | F | 3/3 | 3/3 | 0 | 61.34 / 62.34 | +0.229 | 15,603 | 31.08 | 10.88 | 7.98 | 115.1 | 0 |
| 1 | S | 3/3 | 3/3 | 0 | 65.49 / 73.18 | +0.260 | 6,363 | 11.42 | 3.83 | 7.65 | 91.0 | 0 |
| 1 | A | 3/3 | 3/3 | 0 | 61.70 / 65.36 | +0.276 | 13,018 | 23.65 | 8.84 | 4.89 | 96.9 | 53 |
| 2 | F | 3/3 | 3/3 | 0 | 56.49 / 58.17 | +0.319 | 15,772 | 32.71 | 11.42 | 8.24 | 122.2 | 0 |
| 2 | S | 3/3 | 3/3 | 0 | 58.03 / 65.01 | +0.281 | 6,787 | 12.20 | 4.14 | 7.93 | 98.7 | 0 |
| 2 | A | 3/3 | 3/3 | 0 | 60.07 / 62.59 | +0.277 | 12,815 | 24.20 | 9.02 | 4.96 | 97.6 | 50 |
| 3 | F | 3/3 | 3/3 | 0 | 63.54 / 65.94 | +0.245 | 22,863 | 38.50 | 13.38 | 6.32 | 107.8 | 0 |
| 3 | S | 3/3 | 3/3 | 0 | 69.55 / 72.36 | +0.158 | 10,588 | 13.97 | 4.62 | 5.32 | 78.8 | 0 |
| 3 | A | 3/3 | 3/3 | 0 | 64.46 / 67.70 | +0.261 | 18,837 | 29.07 | 10.94 | 4.23 | 90.8 | 42 |
| 4 | F | 3/3 | 3/3 | 0 | 69.06 / 71.90 | +0.251 | 23,124 | 36.33 | 12.42 | 6.42 | 104.6 | 0 |
| 4 | S | 3/3 | 3/3 | 0 | 69.02 / 72.83 | +0.216 | 12,300 | 13.93 | 4.59 | 6.11 | 84.2 | 0 |
| 4 | A | 3/3 | 3/3 | 0 | 70.50 / 73.88 | +0.234 | 21,572 | 29.55 | 10.96 | 4.27 | 87.0 | 31 |
| 5 | F | 3/3 | 3/3 | 0 | 66.71 / 67.47 | +0.218 | 27,892 | 41.24 | 14.07 | 6.34 | 106.3 | 0 |
| 5 | S | 3/3 | 3/3 | 0 | 70.98 / 74.69 | +0.174 | 13,128 | 15.11 | 4.86 | 6.10 | 81.3 | 0 |
| 5 | A | 3/3 | 3/3 | 0 | 71.44 / 75.07 | +0.233 | 22,744 | 31.62 | 12.05 | 4.06 | 87.3 | 38 |
| 6 | F | 3/3 | 3/3 | 0 | 73.79 / 78.46 | +0.244 | 30,065 | 42.35 | 14.13 | 6.09 | 106.0 | 0 |
| 6 | S | 3/3 | 3/3 | 0 | 87.23 / 95.83 | +0.038 | 16,178 | 14.82 | 4.68 | 5.53 | 76.1 | 0 |
| 6 | A | 3/3 | 3/3 | 0 | 79.41 / 80.62 | +0.240 | 26,059 | 31.20 | 11.70 | 3.79 | 78.1 | 26 |
| 7 | F | 3/3 | 3/3 | 0 | 73.52 / 86.59 | +0.249 | 36,392 | 39.62 | 13.35 | 5.43 | 96.2 | 0 |
| 7 | S | 3/3 | 3/3 | 0 | 76.39 / 85.44 | +0.231 | 18,887 | 15.26 | 4.96 | 5.16 | 77.4 | 0 |
| 7 | A | 3/3 | 3/3 | 0 | 80.97 / 86.90 | +0.249 | 30,768 | 31.46 | 11.43 | 4.07 | 83.0 | 37 |
| 8 | F | 3/3 | 3/3 | 0 | 75.82 / 84.38 | +0.243 | 33,609 | 40.17 | 13.63 | 5.33 | 88.7 | 0 |
| 8 | S | 3/3 | 3/3 | 0 | 75.91 / 77.43 | +0.220 | 18,568 | 15.61 | 5.14 | 5.11 | 77.3 | 0 |
| 8 | A | 3/3 | 3/3 | 0 | 77.54 / 83.25 | +0.241 | 29,265 | 33.10 | 12.36 | 3.61 | 72.5 | 20 |
| 9 | F | 3/3 | 3/3 | 0 | 77.15 / 79.66 | +0.243 | 43,009 | 37.74 | 12.22 | 5.38 | 94.1 | 0 |
| 9 | S | 3/3 | 2/3 | 2 | 83.76 / 90.63 | -0.107 | 24,827 | 14.54 | 4.62 | 4.96 | 76.7 | 0 |
| 9 | A | 3/3 | 3/3 | 0 | 102.04 / 108.58 | +0.188 | 35,866 | 29.63 | 10.47 | 3.40 | 62.3 | 12 |
| 10 | F | 3/3 | 3/3 | 0 | 97.69 / 115.43 | +0.195 | 40,295 | 36.15 | 11.84 | 4.59 | 77.8 | 0 |
| 10 | S | 3/3 | 3/3 | 0 | 85.01 / 88.31 | +0.192 | 23,196 | 14.40 | 4.57 | 4.73 | 72.9 | 0 |
| 10 | A | 3/3 | 3/3 | 0 | 103.70 / 128.46 | +0.205 | 35,775 | 30.93 | 10.98 | 3.24 | 64.8 | 14 |

The effective update rate is `(perf_row_end - perf_row_start + 1) /
mission_time_s`; it is an observed map-update rate, not the 100 Hz FSM timer.

### Computation reduction and switching

| Comparison | Points/update | Map total/update | Occupancy update time | FSM CPU | Mean mission time |
|---|---:|---:|---:|---:|---:|
| Adaptive vs Full | -14.52% | -21.68% | -14.60% | -19.48% | +7.93% |
| Sector vs Full | -47.74% | -62.42% | -63.87% | -20.08% | +3.67% |

Adaptive made 323 effective full-view opens, 10.77 per run. The higher mean
mission time is concentrated in maps9-10; the longest Adaptive run (128.46 s)
continued moving and had 16 arms/22 searches, not an unbounded epoch-reset or
local-escape loop.

Raw: `results/goal_ordered_final_3mode_seed1_10_n3_raw_20260827.csv`

## Verification and claim boundary

`super_planner` rebuilt successfully after the final code change. The build
reported only pre-existing signedness and constructor-order warnings.
`compileall`, 13 unittest cases and 19 pytest cases for the campaign tools all
pass. Source and mirror copies are byte-identical for the six changed files.

This cohort supports the observed statement “Full and Adaptive were 30/30
safety-qualified, while fixed-Sector was 29/30.” It does not prove population
100%, formal collision freedom or hardware-flight readiness. The 95% Wilson
interval lower bound for 30/30 is 88.65%; for 29/30 it is 83.33%. Exact paired
McNemar has only one discordant pair and two-sided `p=1.0`, so this n=3 cohort
alone does not establish a significant mode difference.

Known scope limits remain: `obs_skip_num` is a no-op in the relevant path;
the previously identified NaN and clearance-penalty design defects are not
claimed fixed here; BackupTrajOpt is not covered by all guard evidence; and
`DRONE_R=robot_r` is not an independent physical-contact metric. The rare
single-process RSS explosion in the map8 n=10 campaign remains an unresolved
infrastructure/runtime investigation item, although it did not recur in the
final 90 accepted attempts.
