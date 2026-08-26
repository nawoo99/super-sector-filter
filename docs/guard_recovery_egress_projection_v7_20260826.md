# v7 guarded recovery branch proof and DDA/body-coordinate correction

Date: 2026-08-26
Scope: `v=7`, loop24, static seed maps, raw-cloud CIRI remains shadow-only and
off by default

## Outcome

The recovery-only generation retry and four-way stopped local escape now have
deterministic branch proof. A later 150-run campaign exposed one remaining
Adaptive liveness failure. That failure was not a static-map contact: the
trajectory validator was using an inflated-grid DDA cell centre as though it
were the robot centre when performing a raw occupied-voxel/body-distance test.

The final correction keeps the DDA cell for the efficient inflated-map query,
but projects it onto the actual polynomial chord before measuring physical
body clearance. An initial-footprint egress exception is additionally bounded
to stopped PlanFromRest recovery, and may ignore only a raw cell already
inside the stopped body while the candidate does not move closer to that cell.
Every candidate must still acquire a continuous free tail before commit.

After the correction:

- forced initial-footprint fault: 1/1 complete, injected/committed 1/1,
  static contact 0;
- map 8 Adaptive focused repetition: 5/5 complete, contact 0;
- final map 8-10 Full/Adaptive n=3: 18/18 complete, live/static contact 0,
  speed-valid 18/18, retry 0.

This closes the observed DDA-coordinate liveness defect in the tested local
population. It is not a population-wide or flight-readiness guarantee.

## 1. Recovery branches: deterministic execution evidence

Two test-only, default-off fault paths were added so rare recovery branches
can be tested without weakening production decisions.

### 1.1 Exact generation ACK retry

`--adaptive-test-drop-first-trajectory-guard-full-cloud` makes the native C++
filter publish the trajectory-guard refresh request but intentionally drops
the corresponding first full cloud once. The normal recovery-only
stop-and-wait path must then publish one latest full generation and receive its
exact map-process ACK.

Map 8 Adaptive result:

- complete in 72.76 s;
- dropped full cloud 1, ACK retry frame 1;
- committed exact ACK 32, superseded 1, abandoned 0;
- live/static contact 0, worst static clearance +0.230 m;
- speed-valid.

Raw: `results/ack_fault_injection_seed8_adaptive_raw_20260826.csv`.

### 1.2 Four-way stopped local escape

`SUPER_TEST_FORCE_LOCAL_ESCAPE_ONCE=1` arms one stopped local escape and skips
the first direction. The remaining opposite/perpendicular candidates still
pass through the unchanged hard trajectory certificate.

Map 8 Adaptive result:

- complete in 86.45 s;
- injected 1, first-direction skip 1, certified commit 1;
- live/static contact 0, worst static clearance +0.261 m;
- speed-valid.

Raw: `results/local_escape_forced_seed8_adaptive_raw_20260826.csv`.

These hooks are test instrumentation only. Their CLI/environment defaults are
off and they do not run in the ordinary tight-v7 profiles.

## 2. Pre-fix 150-run campaign

The same-binary, order-crossed map1-10 x Full/Sector/Adaptive x n=5 campaign
gave the intended safety separation for the fixed Sector control, but one
Adaptive liveness failure remained.

| Mode | Complete | Live contact runs/events | Static collision runs/events | Safety-qualified complete | Speed-valid | Mean time (s) |
|---|---:|---:|---:|---:|---:|---:|
| Full | 50/50 | 0/0 | 0/0 | 50/50 | 50/50 | 73.22 |
| fixed Sector | 50/50 | 4/10 | 3/3 | 46/50 | 50/50 | 74.69 |
| Adaptive | 49/50 | 0/0 | 0/0 | 49/50 | 50/50 | 81.29 |

Map-labelled detail:

| Map | Mode | Complete | Live contact runs | Static collision runs | Mean time (s) | Adaptive arm/open | Points/update | Total/update (ms) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Full | 5/5 | 0 | 0 | 62.81 | 0/0 | 15,123 | 34.90 |
| 1 | Sector | 5/5 | 0 | 0 | 64.86 | 0/0 | 7,344 | 12.31 |
| 1 | Adaptive | 5/5 | 0 | 0 | 67.23 | 2/0 | 12,373 | 25.70 |
| 2 | Full | 5/5 | 0 | 0 | 63.46 | 0/0 | 15,456 | 43.56 |
| 2 | Sector | 5/5 | 0 | 0 | 59.22 | 0/0 | 6,621 | 12.81 |
| 2 | Adaptive | 5/5 | 0 | 0 | 60.70 | 4/1 | 9,720 | 19.95 |
| 3 | Full | 5/5 | 0 | 0 | 65.04 | 0/0 | 22,756 | 37.21 |
| 3 | Sector | 5/5 | 0 | 0 | 67.52 | 0/0 | 10,367 | 14.12 |
| 3 | Adaptive | 5/5 | 0 | 0 | 68.34 | 3/0 | 18,290 | 28.66 |
| 4 | Full | 5/5 | 0 | 0 | 73.37 | 0/0 | 24,421 | 36.44 |
| 4 | Sector | 5/5 | 0 | 0 | 71.03 | 0/0 | 12,056 | 13.80 |
| 4 | Adaptive | 5/5 | 0 | 0 | 68.19 | 3/1 | 20,680 | 28.95 |
| 5 | Full | 5/5 | 0 | 0 | 70.11 | 0/0 | 27,718 | 39.64 |
| 5 | Sector | 5/5 | 0 | 0 | 71.60 | 0/0 | 13,386 | 15.03 |
| 5 | Adaptive | 5/5 | 0 | 0 | 78.89 | 2/1 | 23,069 | 32.62 |
| 6 | Full | 5/5 | 0 | 0 | 75.68 | 0/0 | 30,086 | 38.21 |
| 6 | Sector | 5/5 | 0 | 0 | 75.52 | 0/0 | 14,590 | 14.40 |
| 6 | Adaptive | 5/5 | 0 | 0 | 80.27 | 2/1 | 24,466 | 31.22 |
| 7 | Full | 5/5 | 0 | 0 | 79.11 | 0/0 | 36,482 | 39.00 |
| 7 | Sector | 5/5 | 0 | 0 | 86.43 | 0/0 | 19,711 | 14.61 |
| 7 | Adaptive | 5/5 | 0 | 0 | 88.63 | 2/1 | 31,266 | 32.22 |
| 8 | Full | 5/5 | 0 | 0 | 75.47 | 0/0 | 34,328 | 40.51 |
| 8 | Sector | 5/5 | 3 | 2 | 79.80 | 0/0 | 18,547 | 15.57 |
| 8 | Adaptive | 5/5 | 0 | 0 | 81.34 | 4/1 | 28,659 | 33.54 |
| 9 | Full | 5/5 | 0 | 0 | 80.89 | 0/0 | 44,247 | 37.97 |
| 9 | Sector | 5/5 | 1 | 1 | 88.11 | 0/0 | 22,627 | 14.39 |
| 9 | Adaptive | 5/5 | 0 | 0 | 94.25 | 3/4 | 36,441 | 31.08 |
| 10 | Full | 5/5 | 0 | 0 | 86.26 | 0/0 | 41,386 | 37.78 |
| 10 | Sector | 5/5 | 0 | 0 | 82.84 | 0/0 | 22,962 | 14.98 |
| 10 | Adaptive | 4/5 | 0 | 0 | 125.10 | 2/2 | 37,698 | 27.59 |

The single Adaptive failure was map 10 run 4: 240 s, waypoint 0/5, live/static
contact 0, static clearance +0.041 m, 16 reroute arms and 440 reroute searches.
It was an algorithmic stopped-liveness failure, not an infrastructure retry.

Full map 2 run 3 required two infrastructure retries (`no odom samples`) and
then completed. Its row records host available memory falling to 390 MiB,
system swap occupancy 2048 MiB, cgroup swap 1566 MiB, and memory PSI
some/full peaks 97.47/88.25. The planner itself had no OOM delta and zero FSM
swap in the accepted attempt. Inspection found 17,452 stale Fast-DDS shared
memory files using about 4.5 GiB in `/dev/shm`; removing only entries older
than ten minutes restored launch reliability. The final post-fix 18-run gate
had zero retry. This was an accumulated test-infrastructure resource leak, not
evidence that Full's planning algorithm used swap in the successful row.

Raw: `results/final_guarded_velocity_3mode_seed1_10_n5_raw_20260826.csv`.

## 3. Failure sequence and rejected intermediate fixes

### 3.1 Exact occupied-centre/body distance

The physical contact query previously sampled a shell at `robot_r` and asked
which raw voxel contained each shell point. That added voxel quantization to
the physical radius. It was replaced by a direct distance from the candidate
robot centre to occupied raw voxel centres, matching the static-PCD oracle.

Map 10 Adaptive then passed 5/5, but a map1-10 Full/Adaptive n=1 sweep still
had map 9 Adaptive timeout at waypoint 4/5 with static collision 0 and
clearance +0.108 m. Therefore the shell bug was real but not the complete
cause.

### 3.2 Initial-footprint egress, first form

The next form allowed a stopped PlanFromRest candidate to leave a raw occupied
cell already inside its initial robot footprint. It remained bounded by the
escape time/distance window and continuous-free-tail requirement. A forced
fault passed, and map 9 Adaptive passed 3/3, but a fresh map 8 Adaptive run
still stopped at waypoint 2/5.

That map 8 counterexample had a live-cloud contact marker but static-PCD
collision 0 and clearance +0.074 m. All four local directions were rejected at
positions such as `[-24.550, 12.650, 1.750]`, although odometry/trajectory start
was near `[-24.578, 12.667, 1.729]`.

### 3.3 Root cause: DDA cell centre was not the body centre

`map_queries` mixed two coordinate meanings:

1. exact polynomial samples, which are robot centres;
2. inflated-grid DDA cell centres, which only identify traversed map cells.

The raw physical-body test treated both as robot centres. A DDA cell centre can
be displaced by roughly half a voxel from the polynomial chord, so the first
safe escape direction was falsely labelled `OCCUPIED`. This also explains why
the static PCD oracle and online physical query disagreed.

The adopted correction stores both coordinates per query:

- `point`: DDA/inflated-map query coordinate;
- `physical_center`: closest projection onto the sampled polynomial chord.

Raw occupied-voxel distance uses `physical_center`; inflated occupancy still
uses `point`. For initial-footprint egress, a cell already inside the stopped
body is masked only when the candidate-to-cell distance is no smaller than its
initial distance. Moving farther into a real hit therefore remains rejected.

## 4. Post-fix validation

### 4.1 Forced initial-footprint branch

Map 8 Adaptive completed in 73.72 s, with injected/committed footprint egress
1/1, contact 0, static clearance +0.273 m, and valid v7 bound.

Raw: `results/dda_projection_injection_seed8_adaptive_raw_20260826.csv`.

### 4.2 Focused map 8 repetition

Map 8 Adaptive passed 5/5. Mean time was 86.32 s, range 80.11-94.82 s, static
contact 0, minimum static clearance +0.227 m, speed-valid 5/5. The runs
performed 32 topology reroute arms. No natural local-escape or footprint-egress
commit occurred, so deterministic fault injection remains the direct branch
proof.

Raw: `results/dda_projection_seed8_adaptive_n5_raw_20260826.csv`.

### 4.3 Final dense-map Full/Adaptive n=3 gate

| Map | Mode | Complete | Contact | Speed-valid | Mean time (s) | Time range (s) | Worst static clearance (m) | Points/update | Total/update (ms) | FSM CPU (%) | Adaptive arm/open |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | Full | 3/3 | 0 | 3/3 | 70.04 | 67.63-71.41 | +0.244 | 34,514 | 41.39 | 103.19 | 0/0 |
| 8 | Adaptive | 3/3 | 0 | 3/3 | 81.29 | 76.83-87.03 | +0.256 | 28,554 | 32.17 | 72.60 | 2/1 |
| 9 | Full | 3/3 | 0 | 3/3 | 91.91 | 86.37-101.79 | +0.204 | 41,873 | 36.40 | 79.75 | 0/0 |
| 9 | Adaptive | 3/3 | 0 | 3/3 | 92.11 | 79.76-105.74 | +0.197 | 36,667 | 30.62 | 70.42 | 1/3 |
| 10 | Full | 3/3 | 0 | 3/3 | 93.63 | 87.96-104.29 | +0.150 | 41,867 | 36.63 | 74.12 | 0/0 |
| 10 | Adaptive | 3/3 | 0 | 3/3 | 91.84 | 81.11-109.65 | +0.178 | 36,070 | 31.21 | 73.89 | 1/0 |

Overall Full and Adaptive were each 9/9 complete. Adaptive relative to Full:

- points/update: 39,418 -> 33,764, reduction 14.34%;
- map total/update: 38.14 -> 31.33 ms, reduction 17.85%;
- FSM CPU: 85.68% -> 72.30%, reduction 15.62%;
- mean mission time: 85.19 -> 88.42 s, increase 3.78%;
- mean kept percentage: 63.96%;
- full-view arm/open transitions: 4/4.

Raw: `results/dda_projection_dense_full_adaptive_n3_raw_20260826.csv`.

## 5. Code and verification

Source changes were made only in `/root/super_ws/src/SUPER` and mirrored to
`super_patches/native_seedmap_campaign/`:

- `mission_planner_Apps/native_sector_cpp.cpp`;
- `super_planner_include/super_core/config.hpp`;
- `super_planner_include/super_core/super_planner.h`;
- `super_planner_src/super_core/super_planner.cpp`;
- the direct and reliable-filtered tight-v7 YAML profiles.

The campaign runner records ACK-drop, local-escape and footprint-egress branch
markers, supports deterministic fault flags, and can resume only missing
map/run/mode keys with `--resume-existing`.

Verification:

- ROS 2 `super_planner` and `mission_planner` build passed; only the existing
  constructor reorder warning remained;
- source/mirror files are byte-identical;
- `native_campaign.py` compiles;
- 13 Python tests pass;
- final accepted campaigns have no retry/OOM and preserve the v7 speed bound.

## 6. Claim boundary and next step

Do not claim population 100%, formal probability of completion, hardware
flight readiness, or a zero-tolerance `<=7.000000` theorem. The final n=3 gate
is a local regression test. McNemar was not run. `obs_skip_num` remains a no-op
in the investigated path; the known NaN/clearance-penalty design defects and
BackupTrajOpt coverage limitation remain; `DRONE_R=robot_r` alone is not a
sufficient safety metric.

Raw-cloud CIRI remains default false, shadow-only and non-authoritative. The
initial-footprint egress option is enabled only in the two current tight-v7
research profiles and remains false by default in `Config`. It never bypasses
the continuous-free-tail, speed, map-version or candidate-commit checks.

The next meaningful evidence step is a fresh order-crossed map1-10
Full/Sector/Adaptive n=3 or n=5 campaign on this final binary. That campaign
should confirm the intended result simultaneously: Full safe completion,
fixed-Sector degradation, and Adaptive recovery with less mapping work than
Full. Only after repeated clean cohorts should guard long-tail optimization be
resumed.
