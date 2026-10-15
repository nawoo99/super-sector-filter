# Low-speed nearest-face clearance shaping: n=3 gate (2026-08-30)

## 1. Decision

The previous final n=10 campaign left one Adaptive run on map10 with only
`+0.038 m` source-static-PCD body clearance. The event happened at low speed
near a terminal/backup segment; cloud age and exact ACK were normal and the
short replanned tails passed the existing trajectory guard. The remaining gap
was therefore trajectory preference/backup coverage, not another map-delivery
failure.

A hard `0.10 m` terminal-clearance rejection was tested first and rejected. It
turned a soft geometric preference problem into a liveness trap: repeated
candidate rejection could leave the vehicle certified-stopped but unable to
progress. The speed-gated hard variant produced a map10 timeout in its second
run. Both hard-gate source changes were fully reverted.

The retained candidate is a **soft nearest-corridor-face preference** in both
`ExpTrajOpt` and `BackupTrajOpt`:

- normalize each corridor plane before measuring signed distance;
- charge only the nearest face at each quadrature sample, rather than summing
  all faces and making the result depend on CIRI face count;
- use `penna_clr=1.0e6`, `clearance_margin=0.10 m`;
- apply full weight at `v <= 1.5 m/s`, cubic fade to zero over
  `1.5 < v < 2.0 m/s`, and zero weight at `v >= 2.0 m/s`;
- include the speed-envelope derivative in the velocity gradient;
- keep the global/default behavior off when the parameters are absent.

This is a corridor-centering objective, not a hard body-clearance constraint.
The trajectory guard remains the hard acceptance authority.

## 2. Rejected tuning evidence

| Candidate | Cohort actually run | Complete/safe | Mean time | Worst clearance | Decision |
|---|---:|---:|---:|---:|---|
| Hard terminal margin `0.10 m` | map10 n=7, stopped early | 7/7 | 98.59 s | +0.178 m | reject: repeated rejection/long tail |
| Hard margin, low-speed only | map10 n=2, stopped early | 1/2 | 142.24 s | +0.035 m | reject: one 180 s timeout |
| Soft nearest-face, ungated `2e6` | maps9-10 n=10 each | 20/20 | 101.88 s | +0.166 m | reject: map9/10 time +9.3/+15.5% versus prior final |
| Soft nearest-face, ungated `1e6` | maps9-10 n=3 each | 6/6 | 99.46 s | +0.178 m | reject: one 141.01 s recovery tail |
| Soft nearest-face, speed-gated `1e6` | maps9-10 n=3 each | 6/6 | 91.43 s | +0.233 m | pass focused gate |

The accepted focused cohort plus the subsequent three-mode regression gives
six independent runs per difficult map with the same binary/config:

| Map | Runs | Complete/safe | Mean time | Worst clearance |
|---:|---:|---:|---:|---:|
| 9 | 6 | 6/6 | 90.41 s | +0.172 m |
| 10 | 6 | 6/6 | 91.31 s | +0.225 m |

These are sequential cohorts, not a pre-randomized combined experiment.

## 3. Full/Sector/Adaptive map-labelled n=3 gate

The final-binary campaign used maps1-10, three modes, three runs per map/mode,
rotating mode order, static source-PCD collision scoring, strict speed
qualification, reliable filtered link, the validated 1.5/3.0 m/s slowdown
Full refresh and a 180 s timeout. All 90 rows were first-attempt, run-valid,
speed-valid, static-PCD-enabled and performance-window-valid; retry and OOM
counts were zero.

`C/S` below shows `completion ratio · safety-qualified ratio` (each out of
three). Time includes the one Sector timeout so it does not hide the liveness
failure. `Open/run` is Adaptive's effective Sector-to-Full activation count.

| Map | Full C/S | Sector C/S | Adaptive C/S | Mean time F/S/A (s) | Worst clearance F/S/A (m) | Adaptive open/run |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3/3 · 3/3 | 3/3 · 3/3 | 3/3 · 3/3 | 61.1 / 62.6 / 62.9 | +0.256 / +0.209 / +0.276 | 18.7 |
| 2 | 3/3 · 3/3 | 3/3 · 3/3 | 3/3 · 3/3 | 58.6 / 56.3 / 59.8 | +0.264 / +0.203 / +0.284 | 17.0 |
| 3 | 3/3 · 3/3 | 3/3 · 3/3 | 3/3 · 3/3 | 65.0 / 61.8 / 71.0 | +0.255 / +0.301 / +0.249 | 11.7 |
| 4 | 3/3 · 3/3 | 3/3 · 3/3 | 3/3 · 3/3 | 72.3 / 68.7 / 74.6 | +0.220 / +0.234 / +0.250 | 12.0 |
| 5 | 3/3 · 3/3 | 3/3 · 3/3 | 3/3 · 3/3 | 70.7 / 66.2 / 70.9 | +0.215 / +0.215 / +0.214 | 12.0 |
| 6 | 3/3 · 3/3 | 3/3 · 3/3 | 3/3 · 3/3 | 75.7 / 73.7 / 79.9 | +0.260 / +0.221 / +0.266 | 8.7 |
| 7 | 3/3 · 3/3 | 2/3 · 1/3 | 3/3 · 3/3 | 77.9 / 115.0 / 85.5 | +0.145 / -0.172 / +0.226 | 7.3 |
| 8 | 3/3 · 3/3 | 3/3 · 3/3 | 3/3 · 3/3 | 81.4 / 73.2 / 75.1 | +0.196 / +0.197 / +0.153 | 12.0 |
| 9 | 3/3 · 3/3 | 3/3 · 3/3 | 3/3 · 3/3 | 86.6 / 88.4 / 95.1 | +0.163 / +0.146 / +0.172 | 6.3 |
| 10 | 3/3 · 3/3 | 3/3 · 2/3 | 3/3 · 3/3 | 84.0 / 90.5 / 85.5 | +0.191 / -0.059 / +0.225 | 10.3 |

Sector map7 run1 timed out at waypoint 0 without source-PCD collision. Map7
run2 completed but collided (`-0.172 m`), and map10 run2 completed but collided
(`-0.059 m`). The matching Adaptive rows all completed safely. A live-cloud
event in map7 run3 Sector was not source-PCD-confirmed (`+0.103 m`) and is not
counted as a safety collision.

## 4. Aggregate performance

| Mode | Runs | Complete | Safe | Collision runs | Mean time | Completed-only time | Worst clearance |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 30 | 30 | 30 | 0 | 73.33 s | 73.33 s | +0.145 m |
| Sector | 30 | 29 | 27 | 2 | 75.64 s | 72.04 s | -0.172 m |
| Adaptive | 30 | 30 | 30 | 0 | 76.02 s | 76.02 s | +0.153 m |

| Metric | Full | Sector | Adaptive | Adaptive reduction vs Full |
|---|---:|---:|---:|---:|
| Points/update | 29,459.5 | 15,352.5 | 24,806.4 | 15.79% |
| Map update frequency | 6.142 Hz | 6.114 Hz | 4.373 Hz | 28.80% |
| Processed payload | 5.357 MiB/s | 1.693 MiB/s | 2.564 MiB/s | 52.14% |
| Total map time/update | 38.306 ms | 13.511 ms | 30.780 ms | 19.65% |
| Occupancy update time | 13.888 ms | 4.703 ms | 11.990 ms | 13.67% |
| FSM CPU | 103.51% | 85.06% | 86.40% | 16.53% |
| Mission time | 73.33 s | 75.64 s | 76.02 s | **3.67% increase** |

Adaptive made 348 effective Full-view opens, `11.6/run`. Payload is ROG-Map
processed application payload, not NIC/DDS wire bandwidth.

The previous final n=10 baseline had Adaptive worst clearance `+0.038 m` and
mean time `75.81 s`; this candidate n=3 has `+0.153 m` and `76.02 s`.
Specifically, map10 improved `+0.038 -> +0.225 m` while its mean time changed
`86.37 -> 85.51 s`. Map9 remains the caution: its candidate worst clearance is
only `+0.172 m` versus `+0.210 m` in the earlier n=10, so the soft objective is
not monotonic physical-clearance control.

## 5. Statistics and infrastructure boundary

Safety-qualified matched discordance is Full-Sector `3:0`, Sector-Adaptive
`0:3`, and Full-Adaptive `0:0`. Exact two-sided McNemar values are therefore
`0.25`, `0.25`, and `1.0`. The Wilson 95% interval is
`88.65-100%` for Full/Adaptive 30/30 and `74.38-96.54%` for Sector 27/30.
This n=3 gate does not establish population 100%, formal collision freedom,
or hardware-flight readiness.

The host swap was already almost full and peaked near 2,047 MiB, but the FSM
itself used zero swap. Minimum available host memory was 5,561.98 MiB, maximum
FSM RSS was 3,274.52 MiB, memory PSI avg10 was zero, `oom_kill_delta=0`, and
all 90 rows used exactly one attempt. Thus there was no recurrence of the old
infrastructure retry/OOM failure in this campaign.

## 6. Verification and remaining gate

- ROS build: pass (existing warnings only).
- `python3 -m pytest -q scripts/native_campaign`: `20 passed`.
- `git diff --check`: pass.
- All seven mirrored source/config files are byte-identical to the workspace.
- Raw-cloud CIRI remains default false and non-authoritative.

The implementation repairs two previously documented defects: face-summed
clearance cost and missing `BackupTrajOpt` coverage. It does **not** repair the
separate NaN path, the `obs_skip_num` no-op, or the
`DRONE_R=robot_r` metric limitation.

The speed-gated candidate is enabled in the two `tight_v7` validation
profiles, but this is still an n=3 gate. Before calling it the new final
profile, rerun rotating-order maps1-10 x three modes x n=10 (300 rows) with the
same binary and compare against the 2026-08-29 final baseline.

Primary files:

- `results/speed_gated_nearest_face_clearance_3mode_seed1_10_n3_raw_20260830.csv`
- `results/speed_gated_nearest_face_clearance_3mode_seed1_10_n3_summary_20260830.csv`
- `results/speed_gated_nearest_face_clearance_seed9_10_n3_raw_20260830.csv`
- `results/rejected_terminal_margin_seed10_n7_raw_20260830.csv`
- `results/rejected_terminal_margin_speedgate_seed10_n2_raw_20260830.csv`
- `results/rejected_nearest_face_softclr_w2e6_seed9_10_n10_raw_20260830.csv`
- `results/rejected_nearest_face_softclr_w1e6_seed9_10_n3_raw_20260830.csv`
