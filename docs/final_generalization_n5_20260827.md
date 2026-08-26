# Final-binary independent three-mode n=5 generalization gate

Date: 2026-08-27
Scope: `v=7`, loop24, static seed maps 1-10, Full/fixed Sector/Adaptive,
five fresh order-rotated repetitions per map and mode

## Outcome

The fresh 150-run cohort reproduced the intended descriptive research pattern:

| Mode | Complete | Live contact runs/events | Static collision runs/events | Safety-qualified complete | Speed-valid | Mean/median time (s) | Maximum time (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 50/50 | 0/0 | 0/0 | 50/50 | 50/50 | 76.26 / 70.76 | 293.79 |
| fixed Sector | 49/50 | 1/2 | 1/1 | 48/50 | 50/50 | 75.50 / 71.02 | 300.01 |
| Adaptive | 50/50 | 0/0 | 0/0 | 50/50 | 50/50 | 75.10 / 74.56 | 96.30 |

`Safety-qualified complete` requires completion, zero live-cloud contact and
zero static-PCD collision. Full and Adaptive therefore met the requested local
50/50 completion/contact target. Fixed Sector lost one completion on map7 and
made contact on a different map8 run, while Adaptive recovered both paired
runs. This is a fresh generalization cohort and does not reuse the preceding
n=3 rows.

It is not a population guarantee. A 50/50 observation has a two-sided 95%
Wilson completion/contact-free interval of 92.87-100.00%, not a 100% lower
bound. The paired exact McNemar result for safety-qualified completion is only
2:0 discordant pairs, two-sided `p=0.5`.

## Map-labelled results

`Live/static` is the number of runs with each marker, not the event total.
Mean time includes the map7 Sector timeout. `Effective open` is the actual
transition from filtered Sector state into any effective full-view state; its
lower-level causes overlap and must not be added together.

| Map | Mode | Complete | Live/static | Safe complete | Mean time (s) | Range (s) | Worst static clearance (m) | Points/update | Total/update (ms) | FSM CPU (%) | Filter CPU (%) | Kept (%) | Effective open |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Full | 5/5 | 0/0 | 5/5 | 60.69 | 59.27-63.41 | +0.268 | 15,570 | 31.37 | 112.43 | - | - | - |
| 1 | Sector | 5/5 | 0/0 | 5/5 | 60.27 | 54.13-64.47 | +0.289 | 6,900 | 11.76 | 94.51 | 2.42 | 44.64 | - |
| 1 | Adaptive | 5/5 | 0/0 | 5/5 | 62.42 | 60.44-65.63 | +0.200 | 12,830 | 23.82 | 95.41 | 2.65 | 51.39 | 72 |
| 2 | Full | 5/5 | 0/0 | 5/5 | 58.77 | 55.79-63.16 | +0.237 | 15,623 | 31.61 | 111.46 | - | - | - |
| 2 | Sector | 5/5 | 0/0 | 5/5 | 58.57 | 56.47-61.95 | +0.306 | 6,421 | 11.95 | 94.44 | 2.34 | 41.67 | - |
| 2 | Adaptive | 5/5 | 0/0 | 5/5 | 58.61 | 53.80-63.59 | +0.238 | 12,384 | 23.28 | 95.50 | 2.61 | 49.73 | 90 |
| 3 | Full | 5/5 | 0/0 | 5/5 | 64.46 | 61.68-68.97 | +0.278 | 22,568 | 38.48 | 104.40 | - | - | - |
| 3 | Sector | 5/5 | 0/0 | 5/5 | 63.08 | 55.01-75.40 | +0.202 | 10,385 | 13.89 | 90.31 | 2.52 | 44.97 | - |
| 3 | Adaptive | 5/5 | 0/0 | 5/5 | 69.70 | 67.47-71.84 | +0.244 | 19,140 | 29.80 | 84.34 | 2.84 | 57.38 | 56 |
| 4 | Full | 5/5 | 0/0 | 5/5 | 73.51 | 62.05-82.20 | +0.236 | 23,808 | 35.81 | 97.69 | - | - | - |
| 4 | Sector | 5/5 | 0/0 | 5/5 | 66.70 | 61.73-73.58 | +0.111 | 12,211 | 13.86 | 89.48 | 2.67 | 49.59 | - |
| 4 | Adaptive | 5/5 | 0/0 | 5/5 | 71.49 | 65.13-75.87 | +0.253 | 20,993 | 29.11 | 83.99 | 2.86 | 60.05 | 62 |
| 5 | Full | 5/5 | 0/0 | 5/5 | 71.48 | 65.88-78.61 | +0.283 | 26,474 | 40.47 | 94.70 | - | - | - |
| 5 | Sector | 5/5 | 0/0 | 5/5 | 72.23 | 65.91-82.22 | +0.216 | 12,930 | 15.07 | 79.38 | 2.65 | 47.26 | - |
| 5 | Adaptive | 5/5 | 0/0 | 5/5 | 70.90 | 65.70-80.95 | +0.102 | 22,523 | 33.14 | 83.98 | 2.91 | 58.51 | 51 |
| 6 | Full | 5/5 | 0/0 | 5/5 | 70.89 | 64.76-75.62 | +0.226 | 28,951 | 39.26 | 99.03 | - | - | - |
| 6 | Sector | 5/5 | 0/0 | 5/5 | 68.61 | 63.46-74.21 | +0.187 | 15,293 | 14.67 | 90.92 | 2.85 | 51.13 | - |
| 6 | Adaptive | 5/5 | 0/0 | 5/5 | 78.31 | 65.63-89.51 | +0.172 | 25,166 | 30.59 | 77.05 | 3.01 | 61.72 | 42 |
| 7 | Full | 5/5 | 0/0 | 5/5 | 83.87 | 76.60-88.40 | +0.158 | 36,569 | 37.22 | 82.39 | - | - | - |
| 7 | Sector | 4/5 | 0/0 | 4/5 | 120.53 | 65.16-300.01 | +0.130 | 24,642 | 14.60 | 70.60 | 3.32 | 60.47 | - |
| 7 | Adaptive | 5/5 | 0/0 | 5/5 | 84.02 | 78.71-92.22 | +0.163 | 31,214 | 31.07 | 73.39 | 3.09 | 65.06 | 48 |
| 8 | Full | 5/5 | 0/0 | 5/5 | 115.13 | 60.32-293.79 | +0.179 | 36,365 | 37.39 | 87.19 | - | - | - |
| 8 | Sector | 5/5 | 1/1 | 4/5 | 74.34 | 71.01-81.19 | -0.170 | 16,730 | 15.40 | 75.55 | 2.85 | 49.62 | - |
| 8 | Adaptive | 5/5 | 0/0 | 5/5 | 78.70 | 69.67-90.60 | +0.154 | 28,495 | 32.97 | 73.71 | 3.11 | 64.12 | 43 |
| 9 | Full | 5/5 | 0/0 | 5/5 | 79.79 | 70.45-93.13 | +0.207 | 44,616 | 37.18 | 103.95 | - | - | - |
| 9 | Sector | 5/5 | 0/0 | 5/5 | 86.59 | 77.62-95.62 | +0.210 | 23,769 | 14.19 | 71.43 | 3.13 | 55.59 | - |
| 9 | Adaptive | 5/5 | 0/0 | 5/5 | 86.99 | 80.75-92.40 | +0.182 | 36,416 | 30.13 | 72.26 | 3.29 | 65.08 | 35 |
| 10 | Full | 5/5 | 0/0 | 5/5 | 84.03 | 72.08-93.84 | +0.185 | 41,670 | 36.69 | 91.60 | - | - | - |
| 10 | Sector | 5/5 | 0/0 | 5/5 | 84.05 | 76.33-90.21 | +0.032 | 23,591 | 14.14 | 74.90 | 3.14 | 55.36 | - |
| 10 | Adaptive | 5/5 | 0/0 | 5/5 | 89.82 | 82.87-96.30 | +0.206 | 35,109 | 31.02 | 72.98 | 3.17 | 64.26 | 35 |

## Adaptive computation and switching

All 50 Full/Adaptive map-run pairs have a valid, generation-specific
performance window. Relative to Full, Adaptive reduced the aggregate mean:

- points/update by 16.41% (`29,221 -> 24,427`);
- map total/update by 19.31% (`36.55 -> 29.49 ms`);
- occupancy-cache update time by 11.74% (`12.38 -> 10.93 ms`);
- FSM CPU by 17.49% (`98.48 -> 81.26%`).

Adaptive retained 59.73% of input points on average. It made 534 effective
full-view opens, or 10.68 per mission. The lower-level counters were stall
arm/open 27/14, replan-guard open 1,218 and trajectory-guard open 276. They
overlap in time, so only 534 is the actual state-transition count.

Time-integrated FSM+filter CPU work fell 13.33%. The campaign-wide
update-count-weighted point and mapping work fell 46.76% and 46.04%, but those
totals are strongly affected by the Full map8 run2 long tail and are secondary
to the per-update figures above. Mean mission time was 1.53% lower for
Adaptive because that Full outlier raises the Full mean; the paired median
Adaptive-minus-Full difference was instead +1.48 s, and Adaptive was faster on
20/50 pairs. The mode medians (`70.76 s` Full and `74.56 s` Adaptive) show the
usual small time cost more clearly.

For context, fixed Sector reduced Full points/update 47.68%, total/update
61.82%, update time 63.21% and FSM CPU 15.57%, but lost one completion and one
different run's safety. Adaptive recovers the observed safety/liveness while
retaining a smaller, measurable part of the computation saving.

The exact-generation link remained closed: Adaptive recorded 1,336/1,336
trajectory-guard full-refresh ACK commits, 3,656/3,656 pre-stale ACK commits,
and zero retry, pending, superseded, abandoned or ACK-timeout result.

## Paired counterexamples and remaining liveness tail

- Map7 run1 fixed Sector stopped after waypoint 4/5 and timed out at 300.01 s.
  It remained contact-free with +0.130 m worst static clearance, but repeatedly
  rejected the zero-speed emergency-stop retry instead of producing a new
  topology. Paired Full completed in 88.40 s and Adaptive in 80.80 s; Adaptive
  made ten effective full-view opens.
- Map8 run1 fixed Sector completed in 74.66 s but made two live contact events
  and one static-PCD collision. The first live marker was at 13.5102 s,
  `[19.585, 23.577, 2.246]`, at 6.629 m/s; worst static clearance was -0.170 m.
  Paired Full completed in 74.23 s with +0.239 m and Adaptive in 69.67 s with
  +0.286 m, both contact-free. Adaptive made 13 effective full-view opens.
- Map8 run2 Full spent most of the mission stopped at
  `[-24.725, 12.575, 1.675]` while guarded A* returned `NO_PATH`. It finally
  recovered after 154 topology arms and 363 searches and completed in 293.79 s,
  only 6.21 s before timeout. Paired Adaptive completed in 81.30 s with two
  arms/two searches and contact 0. This is not a Full completion failure in
  the measured gate, but it is a real liveness-tail defect and explains why
  the Full mean must be reported with its median and maximum.

The n=5 map9 Sector contact from the earlier n=3 gate did not reproduce; all
three map9 modes were 5/5 and contact-free. The new contact moved to map8.
That observation supports treating limited-view degradation as stochastic and
trajectory-dependent rather than as a deterministic property of one seed.

## Statistical boundary and consistency with n=3

The independent n=5 exact paired McNemar tests are not significant: completion
Full/Sector and Adaptive/Sector each have discordance 1:0 and `p=1.0`;
contact-free status also has 1:0 and `p=1.0`; safety-qualified completion has
2:0 and `p=0.5`.

As a supplementary same-binary descriptive pool, n=3+n=5 gives Full 80/80,
Sector 78/80 and Adaptive 80/80 completion; contact-free status is 80/80,
76/80 and 80/80; safety-qualified completion is 80/80, 75/80 and 80/80. The
pooled safety McNemar discordance is 5:0 with two-sided `p=0.0625`, still above
0.05. The direction is consistent, but the next evidence should come from
held-out layouts/noise rather than repeatedly sampling only the same ten maps.

## Infrastructure, verification and claim boundary

All 150 rows were first-attempt, retry 0, OOM delta 0, speed-valid, performance
generation-ready and performance-window-valid. FSM swap was 0 throughout;
minimum available host memory was 4.65 GiB, host swap occupancy stayed in the
1.058-1.063 GiB range, cgroup peak swap was at most 103.00 MiB, and sampled
memory PSI was 0. The prior stale Fast-DDS pressure did not recur. After the
campaign `/dev/shm` used 238 MiB with 908 Fast-DDS files, far below the earlier
4.5 GiB/17,452-file failure state.

Raw data is
`results/final_generalization_3mode_seed1_10_n5_raw_20260827.csv`.
`py_compile`, 13 unittest cases and all 19 pytest cases pass.

This result establishes the requested pattern only for the observed local
cohort. It does not establish population-wide 100%, formal collision freedom,
or hardware flight readiness. Raw-cloud CIRI remains default false,
shadow-only and non-authoritative. The known `obs_skip_num` no-op,
NaN/clearance-penalty defects, BackupTrajOpt coverage limitation and
`DRONE_R=robot_r` metric limitation remain outside this correction.

The next engineering target is to bound the Full map8 stopped-search tail by
reusing or invalidating certified topology information without weakening the
hard certificate. The next experimental target is an order-rotated held-out
map/noise cohort with a preregistered paired safety endpoint.
