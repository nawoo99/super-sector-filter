# Full endpoint hard guard + Adaptive commit refresh n=1 gate (2026-08-23)

## Scope

This gate validates two changes on `loop24.txt`, v=7, static PCD, timeout
240 s, and seed1-10 once per mode. Mode order continued rotating across seed
boundaries. Full used direct `/cloud_registered`; Sector and Adaptive used the
native C++ strict-burst filter and `/cloud_sector`.

The Full fix makes the actual current odometry pose, the first checked
trajectory pose, and the terminal pose mandatory raw-occupied body-clearance
queries. These queries use `robot_r`, are outside the initial-clearance escape
exception, and run before a short tail can become a stationary hold.

The Adaptive fix publishes `/rog_map/commit_version` after a committed map
update. When the normal 5 Hz output cap is blocking and the last commit ACK is
at least 0.12 s old, the filter may publish one sector-only latest-frame
refresh, no faster than every 0.10 s. During an effective full-open frame, the
normal sector and near-field points remain complete while at most 6,000
deterministically sampled far-field points are added. Raw-cloud CIRI remains
default false.

## Verification

- `colcon build --symlink-install --packages-select rog_map mission_planner super_planner`:
  PASS (3 packages, 7 min 38 s; only existing warnings).
- Native C++ filter synthetic equivalence: PASS, all 3 expected points retained.
- Python campaign/monitor/shadow checks: PASS.
- Full seed7 smoke: 5/5 waypoints, contact 0, static body clearance +0.230 m.
- Adaptive seed9 smoke: 5/5, contact 0, 126.57 s; 60 commit-refresh frames
  and 4.06 commit ACK/s. `MAP_STALE` fell to 23 and successful brakes to 29,
  but topology/optimizer retries still dominated elapsed time.
- Main campaign: 30 rows in 46.9 min; every row valid, one attempt, retry 0.

## Main n=1 result

`safe completion` requires all five waypoints and zero live/static contact.
Mission-time means include the Sector seed10 timeout; its completed-run-only
mean is 76.466 s.

| Mode | Raw completion | Safe completion | Contact runs/events | Worst static body clearance | Mean mission | Map commits | Points/update | Mapping/update | Mapping work/mission | Combined CPU-work/mission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 10/10 | 10/10 | 0/0 | +0.252 m | 72.679 s | 5.612 Hz | 29,321 | 35.363 ms | 14.425 s | 67.800 s |
| Sector | 9/10 | 9/10 | 0/0 | +0.108 m | 92.820 s | 5.048 Hz | 15,717 | 13.257 ms | 6.212 s | 62.628 s |
| Adaptive | 10/10 | 10/10 | 0/0 | +0.174 m | 85.875 s | 3.336 Hz | 18,679 | 18.509 ms | 5.303 s | 57.573 s |

All 30 runs had zero live contact events and zero static-PCD contact episodes.
Full and Adaptive met the requested descriptive 10/10 safety/completion gate;
Sector seed10 stopped after waypoint 4 and timed out safely at 240.01 s.

Relative to Full in this cohort, Adaptive reduced map commits 40.56%,
points/update 36.30%, throughput 62.13%, mapping/update 47.66%, mapping
work/mission 63.24%, and combined CPU-work/mission 15.08%. Mean mission time
was 18.16% longer. Sector's 27.71% all-run time increase is driven by its one
timeout; among its nine completions the mean was 76.466 s.

## Per-seed table

Times are seconds. Parentheses mark incomplete waypoints. `A open/close` is
the actual combined Adaptive output edge count, not a component counter.

| Seed | Full | Sector | Adaptive | Adaptive - Full | Full/Sector/Adaptive static clearance | A open/close | Commit refresh | Commit ACK Hz |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 52.14 | 59.27 | 60.36 | +8.22 | +.307 / +.288 / +.292 | 24/24 | 17 | 4.64 |
| 2 | 56.17 | 57.25 | 59.64 | +3.47 | +.318 / +.252 / +.334 | 23/23 | 29 | 4.90 |
| 3 | 71.02 | 68.31 | 69.35 | -1.67 | +.303 / +.316 / +.278 | 22/22 | 9 | 3.60 |
| 4 | 75.50 | 99.11 | 70.20 | -5.30 | +.252 / +.167 / +.284 | 25/25 | 25 | 3.83 |
| 5 | 85.05 | 71.84 | 80.67 | -4.38 | +.278 / +.300 / +.272 | 25/25 | 18 | 3.24 |
| 6 | 71.62 | 84.94 | 83.93 | +12.31 | +.311 / +.173 / +.250 | 25/25 | 30 | 3.16 |
| 7 | 81.42 | 89.72 | 103.50 | +22.08 | +.293 / +.196 / +.271 | 24/24 | 35 | 2.88 |
| 8 | 67.99 | 67.68 | 96.07 | +28.08 | +.277 / +.206 / +.284 | 26/26 | 19 | 3.00 |
| 9 | 80.49 | 90.07 | 116.12 | +35.63 | +.274 / +.229 / +.174 | 54/54 | 74 | 3.13 |
| 10 | 85.39 | 240.01 (4/5) | 118.91 | +33.52 | +.283 / +.108 / +.257 | 41/41 | 53 | 2.71 |

Adaptive generated 289 full-open and 289 full-close edges, 28.9 opens/run,
with 20.97% mean time-weighted open duty. It published 309 bounded commit
refreshes and received 2,889 commit ACKs (3.364 ACK/s using total mission
time). The full-open budget considered 7,560,583 far-field candidates and kept
4,091,907; complete sector/near-field points are not included in that budget.

## Effect of the Adaptive timing fix

The preceding order-crossed n=5 campaign is the larger reference, but this
n=1 gate is not a paired statistical comparison. Directionally, Adaptive map
commits rose from 2.944 to 3.336 Hz (+13.33%). Mean `MAP_STALE` observations
fell from 70.86 to 61.30/run (-13.49%), successful brakes from 45.84 to
38.80/run (-15.36%), and mission time from 92.122 to 85.875 s (-6.78%). Full
also varied from 75.292 to 72.679 s (-3.47%), so the cleaner relative result is
that the Adaptive-vs-Full time penalty narrowed from 22.35% to 18.16%.

The fix does not eliminate the late-seed liveness cost. On seed9, compared
with the old n=5 mean, `MAP_STALE` fell 118.8 -> 84 and brakes 74.6 -> 59,
but topology reroute arm/search rose 11.0/14.4 -> 19/25. Seed10 similarly
recorded 11/24 arm/search events. Thus map starvation was a real contributor,
but after refreshing commits the remaining seed9/10 delay is dominated by
the geometric topology/optimizer recovery workload rather than repeated
same-candidate map staleness.

## Safety and evidence limits

The old Full seed7 contact was rare (1/5). The new Full seed7 smoke plus main
gate produced two safe runs, and all ten Full seeds were safe, but no
`status=OCCUPIED` hard-endpoint rejection occurred. Therefore this campaign
shows no regression and removes the identified code-level hole; it does not
execution-prove the rare reject branch or establish population-level 100%.
At n=10, even 10/10 has an exact two-sided 95% lower confidence bound of about
69.15%. A repeated seed7/seed1-10 gate is still required before a paper-level
safety claim.

Memory remained bounded: attempt/retry was 1/0 for every row, OOM delta and
FSM swap were zero, peak FSM RSS/PSS was 3476.25/3452.99 MiB, and minimum host
available memory was 4821.88 MiB. Host swap was already about 2 GiB occupied.
Sector seed10 showed a brief host-wide PSI some/full 0.12 during its 240 s
stall, but there was no FSM swap, OOM, or infrastructure retry.

Artifacts:

- `results/endpoint_commitrefresh_3mode_strict_v7_n1_raw_20260823.csv`
- `results/endpoint_commitrefresh_3mode_strict_v7_n1_summary_20260823.csv`
- `results/endpoint_commitrefresh_3mode_strict_v7_n1_seed_summary_20260823.csv`
