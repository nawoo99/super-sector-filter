# Final DDA-projection three-mode n=3 gate

Date: 2026-08-26
Scope: `v=7`, loop24, static seed maps 1-10, Full/fixed Sector/Adaptive,
three order-rotated repetitions per map and mode

## Outcome

The final DDA/body-coordinate binary passed the intended local research gate:

| Mode | Complete | Live contact runs/events | Static collision runs/events | Safety-qualified complete | Speed-valid | Mean time (s) |
|---|---:|---:|---:|---:|---:|---:|
| Full | 30/30 | 0/0 | 0/0 | 30/30 | 30/30 | 71.67 |
| fixed Sector | 29/30 | 3/6 | 3/3 | 27/30 | 30/30 | 79.41 |
| Adaptive | 30/30 | 0/0 | 0/0 | 30/30 | 30/30 | 75.91 |

Full and Adaptive therefore achieved 100% completion and zero measured
contact in this 30-run local population. Fixed Sector lost one completion and
had contact on maps 5 and 9. In map9 run1, Sector completed with -0.160 m
static clearance while the paired Adaptive completed in 84.73 s with zero
contact and +0.282 m clearance. In map9 run2, Sector contacted and timed out at
300 s, while Adaptive completed in 89.74 s with zero contact and +0.265 m
clearance.

This is the intended experimental separation, but it is not a proof of
population-wide 100%, a formal collision guarantee, or flight readiness.

## Map-labelled results

`Live/static` reports contact runs, not event totals. `Effective open` is the
actual transition from filtered Sector state to any effective full-view state;
it includes overlapping stall, replan-guard and trajectory-guard causes.

| Map | Mode | Complete | Live/static contact runs | Safe complete | Mean time (s) | Range (s) | Worst static clearance (m) | Points/update | Total/update (ms) | FSM CPU (%) | Filter CPU (%) | Kept (%) | Effective open |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Full | 3/3 | 0/0 | 3/3 | 58.31 | 57.14-59.03 | +0.239 | 15,326 | 30.94 | 118.14 | - | - | - |
| 1 | Sector | 3/3 | 0/0 | 3/3 | 60.34 | 58.93-63.00 | +0.276 | 6,679 | 11.93 | 96.22 | 2.41 | 43.31 | 0 |
| 1 | Adaptive | 3/3 | 0/0 | 3/3 | 60.60 | 59.26-61.28 | +0.162 | 12,015 | 23.06 | 97.15 | 2.71 | 48.50 | 52 |
| 2 | Full | 3/3 | 0/0 | 3/3 | 57.50 | 54.15-59.47 | +0.254 | 15,739 | 32.98 | 116.60 | - | - | - |
| 2 | Sector | 3/3 | 0/0 | 3/3 | 54.13 | 52.37-57.54 | +0.272 | 6,560 | 12.46 | 100.42 | 2.45 | 42.42 | 0 |
| 2 | Adaptive | 3/3 | 0/0 | 3/3 | 57.90 | 56.60-59.40 | +0.208 | 12,187 | 22.90 | 99.03 | 2.66 | 48.65 | 54 |
| 3 | Full | 3/3 | 0/0 | 3/3 | 65.14 | 60.71-69.55 | +0.242 | 22,458 | 38.35 | 98.19 | - | - | - |
| 3 | Sector | 3/3 | 0/0 | 3/3 | 72.11 | 65.28-79.15 | +0.233 | 10,306 | 14.43 | 83.71 | 2.58 | 44.98 | 0 |
| 3 | Adaptive | 3/3 | 0/0 | 3/3 | 66.93 | 64.03-69.61 | +0.273 | 18,325 | 29.41 | 90.62 | 2.87 | 54.02 | 42 |
| 4 | Full | 3/3 | 0/0 | 3/3 | 68.98 | 66.31-70.86 | +0.214 | 23,938 | 37.07 | 103.12 | - | - | - |
| 4 | Sector | 3/3 | 0/0 | 3/3 | 72.02 | 70.76-73.43 | +0.229 | 13,018 | 14.01 | 89.68 | 2.74 | 51.61 | 0 |
| 4 | Adaptive | 3/3 | 0/0 | 3/3 | 75.90 | 65.35-82.61 | +0.185 | 20,966 | 30.03 | 82.39 | 2.89 | 61.19 | 32 |
| 5 | Full | 3/3 | 0/0 | 3/3 | 73.03 | 66.98-82.78 | +0.229 | 26,866 | 40.05 | 93.21 | - | - | - |
| 5 | Sector | 3/3 | 1/1 | 2/3 | 68.74 | 65.71-71.24 | -0.018 | 13,244 | 15.48 | 85.45 | 2.71 | 47.61 | 0 |
| 5 | Adaptive | 3/3 | 0/0 | 3/3 | 73.63 | 72.04-74.70 | +0.222 | 22,182 | 32.88 | 81.48 | 2.87 | 56.81 | 36 |
| 6 | Full | 3/3 | 0/0 | 3/3 | 80.52 | 74.72-84.29 | +0.246 | 29,798 | 39.15 | 88.81 | - | - | - |
| 6 | Sector | 3/3 | 0/0 | 3/3 | 69.64 | 66.36-73.15 | +0.233 | 15,580 | 14.92 | 88.16 | 2.87 | 51.41 | 0 |
| 6 | Adaptive | 3/3 | 0/0 | 3/3 | 78.56 | 69.83-83.72 | +0.236 | 23,898 | 31.73 | 85.73 | 3.02 | 57.93 | 30 |
| 7 | Full | 3/3 | 0/0 | 3/3 | 80.93 | 68.74-91.48 | +0.242 | 36,704 | 40.38 | 96.21 | - | - | - |
| 7 | Sector | 3/3 | 0/0 | 3/3 | 87.01 | 78.84-96.05 | +0.200 | 20,794 | 15.15 | 73.00 | 2.98 | 55.56 | 0 |
| 7 | Adaptive | 3/3 | 0/0 | 3/3 | 81.61 | 75.20-93.72 | +0.176 | 30,386 | 33.62 | 75.55 | 3.12 | 64.88 | 16 |
| 8 | Full | 3/3 | 0/0 | 3/3 | 68.56 | 65.16-74.83 | +0.264 | 35,340 | 43.23 | 108.64 | - | - | - |
| 8 | Sector | 3/3 | 0/0 | 3/3 | 75.07 | 72.40-78.70 | +0.224 | 16,954 | 16.01 | 77.05 | 2.92 | 50.10 | 0 |
| 8 | Adaptive | 3/3 | 0/0 | 3/3 | 90.96 | 89.29-91.92 | +0.234 | 28,886 | 33.81 | 67.26 | 3.14 | 63.52 | 17 |
| 9 | Full | 3/3 | 0/0 | 3/3 | 79.60 | 74.30-88.89 | +0.179 | 44,049 | 38.93 | 102.77 | - | - | - |
| 9 | Sector | 2/3 | 2/2 | 1/3 | 153.52 | 76.12-300.01 | -0.173 | 40,576 | 11.82 | 66.45 | 3.84 | 68.19 | 0 |
| 9 | Adaptive | 3/3 | 0/0 | 3/3 | 86.26 | 84.32-89.74 | +0.166 | 37,630 | 31.69 | 75.42 | 3.26 | 66.34 | 25 |
| 10 | Full | 3/3 | 0/0 | 3/3 | 84.17 | 76.32-92.39 | +0.231 | 42,499* | 38.33* | 94.92 | - | - | - |
| 10 | Sector | 3/3 | 0/0 | 3/3 | 81.50 | 78.42-84.18 | +0.244 | 23,303 | 15.12 | 76.27 | 3.14 | 55.28 | 0 |
| 10 | Adaptive | 3/3 | 0/0 | 3/3 | 86.69 | 85.43-87.86 | +0.226 | 35,709 | 32.39 | 71.45 | 3.18 | 66.12 | 17 |

`*` Map10 Full computation means contain 2/3 rows because run1 exposed the
performance-log startup race described below. Completion, contact, clearance,
speed, mission time, CPU and memory fields for that row remain valid.

## Adaptive reduction and transition accounting

The fair per-update comparison excludes the missing map10 run1 Full metric and
its paired Adaptive row, leaving 29 matched map/run pairs. Adaptive relative
to Full reduced:

- points/update 17.22%;
- map total/update 20.70%;
- occupancy-cache update time 13.03%;
- FSM CPU 19.12%.

Across all 30 runs, mean mission time increased 5.91%. Time-integrated
FSM+filter CPU work decreased 11.66%. Adaptive retained 58.80% of input points
on average. It made 321 actual effective full-view open transitions. The
lower-level stall state recorded arm/open 14/5; trajectory-guard open events
were 158. These counts must not be added because their active intervals can
overlap.

Adaptive had 813 planner recovery-gate arms and 812 planner-side recovery ACK
markers. The filter independently recorded 813/813 trajectory-guard exact ACKs,
with zero pending, superseded generation, abandon or ACK-SLA timeout. The
one-marker difference is therefore a counter-scope/order boundary, not a
missing delivered ACK or an in-run resume without ACK. Natural local-escape
and initial-footprint egress commits were both zero; their direct execution
evidence remains the default-off deterministic tests in the preceding DDA
document.

## Performance-log startup race and correction

Map10 Full run1 recorded `perf_row_start=472`, `perf_row_end=446`, so its
mapping metrics were correctly left empty. The shared ROG-Map CSV is opened
with `std::ios::trunc` in `ROGMap::init()`. On a large static map, initialization
can finish after the runner's fixed four-second startup delay. The runner can
therefore sample the previous process's row count immediately before the new
process truncates the file.

The runner now:

1. captures the performance-log signature immediately before launch;
2. waits for a changed generation with a valid ROG-Map header;
3. starts the measurement window only after that generation exists;
4. checks `row_end > row_start`;
5. copies the complete per-attempt performance CSV before process teardown and
   computes the slice from that immutable snapshot.

A post-fix map10 three-mode n=1 gate passed all three modes with contact 0,
valid speed, `perf_log_generation_ready=true`, and
`perf_window_valid=true`:

| Mode | Complete | Static contact | Time (s) | Perf rows | Points/update | Total/update (ms) | FSM CPU (%) | Filter CPU (%) | Kept (%) | Effective open |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 1/1 | 0 | 80.88 | 453 | 40,369 | 35.11 | 86.44 | - | - | - |
| Sector | 1/1 | 0 | 76.34 | 421 | 24,384 | 15.63 | 82.98 | 3.32 | 56.55 | 0 |
| Adaptive | 1/1 | 0 | 96.18 | 346 | 35,531 | 31.33 | 70.53 | 3.28 | 65.87 | 4 |

On this instrumentation gate, Adaptive reduced Full points/update 11.98%,
total/update 10.75%, total point work 32.77%, and total mapping work 31.83%.
The single-run mission was 18.92% longer and combined CPU work was 1.54%
higher, which illustrates why the broader n=3 CPU/time result should be used
instead of substituting this n=1 observation.

## Infrastructure and verification

All 90 broad runs and all three instrumentation runs succeeded on their first
attempt: retry 0, OOM delta 0 and FSM swap 0. Broad-campaign minimum available
host memory was 5.10 GiB; the maximum memory-PSI sample was 0.18/0.18. The
earlier stale Fast-DDS `/dev/shm` failure did not recur.

Raw data:

- `results/final_dda_projection_3mode_seed1_10_n3_raw_20260826.csv`;
- `results/perf_generation_seed10_3mode_n1_raw_20260826.csv`.

`native_campaign.py` and all native-campaign Python files compile, and all 19
Python tests pass. Raw-cloud CIRI remains default false, shadow-only and
non-authoritative. McNemar was not run. The known `obs_skip_num` no-op,
NaN/clearance-penalty defects, BackupTrajOpt coverage limitation, and
`DRONE_R=robot_r` metric limitation remain outside this correction.
