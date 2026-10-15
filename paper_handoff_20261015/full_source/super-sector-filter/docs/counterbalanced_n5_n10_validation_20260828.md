# Final candidate crossed-order n=5 and n=10 validation

Date: 2026-08-27--28

## Scope and result status

This document validates the frozen v=7 candidate with globally rotated mode
order.  The first gate is maps 1--10 x Full/Sector/Adaptive x n=5 (150 fresh
process runs).  A second maps 1--10 x three modes x n=10 campaign is recorded
separately below; it must not be silently pooled with n=5.

The n=5 gate completed all 150 missions, with valid speed and zero static-PCD
body intersections.  The legacy live-cloud detector emitted two episodes in
one Sector map8 run and one episode in one Adaptive map10 run.  Event-level
geometry shows that all three were outside the source static PCD at the actual
vehicle pose.  Therefore these remain visible as live-render markers, while
the common static-map safety authority is reported independently.

Raw n=5 data:
`results/counterbalanced_candidate_3mode_seed1_10_n5_raw_20260827.csv`.

## Protocol

- Mission: `loop24.txt`, v=7, 180 s timeout, five waypoints.
- Maps: seed1 through seed10.
- Modes: direct Full, fixed body-yaw Sector, velocity-aligned Adaptive.
- Filter: `strict-burst`, C++ backend, reliable depth-1 filtered map link.
- Planner profiles:
  `static_seedmaps_guard_viability_tight_v7.yaml` and
  `static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml`.
- Static source PCD enabled and required for every accepted row.
- Raw-cloud CIRI shadow remained disabled and non-authoritative.
- Order rotates continuously across map boundaries.  The 50 block positions
  are Full 17/16/17, Sector 17/17/16 and Adaptive 16/17/17 for positions
  1/2/3 respectively.  This removes the earlier fixed Full->Sector->Adaptive
  order confound as closely as possible with 50 blocks.

## n=5 map-labelled result

`safe` below means completed, run-valid, speed-valid and zero static-PCD body
intersection.  `live` is the legacy rendered-cloud episode count and is kept
separate rather than overwritten.

| map | Full complete/safe · live | Sector complete/safe · live | Adaptive complete/safe · live | mean time F/S/A (s) | Adaptive effective opens |
|---:|:---:|:---:|:---:|---:|---:|
| 1 | 5/5 · 0 | 5/5 · 0 | 5/5 · 0 | 57.35 / 61.13 / 63.42 | 83 |
| 2 | 5/5 · 0 | 5/5 · 0 | 5/5 · 0 | 57.70 / 58.17 / 58.95 | 83 |
| 3 | 5/5 · 0 | 5/5 · 0 | 5/5 · 0 | 69.64 / 64.72 / 69.19 | 53 |
| 4 | 5/5 · 0 | 5/5 · 0 | 5/5 · 0 | 70.24 / 64.33 / 72.44 | 52 |
| 5 | 5/5 · 0 | 5/5 · 0 | 5/5 · 0 | 70.82 / 63.11 / 71.03 | 59 |
| 6 | 5/5 · 0 | 5/5 · 0 | 5/5 · 0 | 75.32 / 74.02 / 80.22 | 50 |
| 7 | 5/5 · 0 | 5/5 · 0 | 5/5 · 0 | 84.10 / 78.08 / 81.47 | 46 |
| 8 | 5/5 · 0 | 5/5 · 2 | 5/5 · 0 | 73.17 / 73.03 / 76.24 | 55 |
| 9 | 5/5 · 0 | 5/5 · 0 | 5/5 · 0 | 86.09 / 95.67 / 84.35 | 45 |
| 10 | 5/5 · 0 | 5/5 · 0 | 5/5 · 1 | 85.90 / 88.74 / 85.07 | 48 |
| **total** | **50/50 · 0** | **50/50 · 2** | **50/50 · 1** | **73.03 / 72.10 / 74.24** | **574** |

Sector's two live episodes belong to one map8 run; Adaptive's one episode is
one map10 run.  Run counts and episode counts must not be interchanged.

## n=5 computation and payload

Values are means over 50 accepted runs per mode.  Payload is the processed
ROG-Map application payload observed by the campaign, not NIC/DDS wire rate.

| metric | Full | Sector | Adaptive | Sector vs Full | Adaptive vs Full |
|:---|---:|---:|---:|---:|---:|
| mission time (s) | 73.03 | 72.10 | 74.24 | -1.28% | +1.65% |
| points/update | 29,147 | 14,920 | 24,349 | -48.81% | -16.46% |
| map total/update (ms) | 36.897 | 14.129 | 29.585 | -61.71% | -19.82% |
| processed payload (Mbit/s) | 44.169 | 13.365 | 19.454 | -69.74% | -55.96% |
| FSM CPU (%) | 100.40 | 84.91 | 84.21 | -15.43% | -16.13% |
| effective full-view opens | 0 | 0 | 574 | - | 11.48/run |

These reductions are cohort observations, not hardware-network bandwidth or
population guarantees.  The raw update-weighted aggregation will be reported
alongside these run means in the final n=10 section.

## Adaptive map10 live-only event investigation

The n=5 Adaptive map10 run4 mission completed all waypoints in 81.84 s with
valid v=7 speed.  Its live detector emitted one event at 23.9187 s and
1.27471 m/s: centre-to-rendered-point distance 0.19858 m, only 1.42 mm inside
the legacy 0.20 m threshold.  The exact source-PCD distance at that same pose
was 0.315942 m, or +0.115942 m body clearance.  The rendered point itself was
0.120255 m from the nearest source-PCD sample.  The run-wide source-PCD
minimum remained 0.274 m (+0.074 m body clearance), with zero static contact.

The MARSIM configuration uses `downsample_res=0.1`; its renderer expands each
source point across adjacent angular pixels with
`cover_dis=0.55*sqrt(3)*downsample_res`, approximately 0.0953 m.  Thus the
live cloud is a perception/render product and not the source geometry oracle.
The planner still consumes that product, so the event is retained as a
diagnostic; it is not relabelled as a common physical intersection.

The older n=5 Sector map8 live events have the same distinction.  At the two
event poses the exact source-PCD body clearances were +0.059149 m and
+0.006297 m, while the rendered points were 0.095593 m and 0.067592 m from
the source PCD.  The second is a genuine close pass, but neither crossed the
static body boundary.

The monitor now preserves the historical live fields and additionally emits:

- `safety_contact_source` and `safety_collisions`;
- live-only and static-confirmed live event counts;
- source-PCD distance/clearance at the first event; and
- rendered-contact-point distance from the source PCD.

No planner or flight-decision parameter changed.  A post-instrumentation
Adaptive map10 n=5 focus gate completed 5/5, with zero live/static contact,
valid speed, no retry/OOM and source-PCD clearances +0.233, +0.225, +0.250,
+0.122 and +0.183 m.  Raw:
`results/live_static_authority_seed10_adaptive_n5_raw_20260828.csv`.

## n=10 crossed-order gate

### Rejected attempts and fixes before the final gate

The first n=10 attempt stopped at 132/300 rows when map5 Full run4 reached the
180 s mission timeout.  Goal-direction fallback was added only as an ordering
seed for the existing stop-only eight-direction local-escape candidates in
three degenerate collision-direction branches.  It did not change the
trajectory/viability certificate, thresholds or recovery budget.  Focused
map5 Full n=3+n=5 then completed 8/8 first-attempt and static-contact-free.
The new `direction_source=goal_fallback` branch did not occur naturally, so
these runs are regression evidence, not direct proof that this branch caused
the recovery.

A restarted candidate reached 277/300 saved rows, then map10 run3 Full's
`fsm_node` was killed by the kernel before its row could be committed.  This
was not the 180 s planner timeout: the memory trace rose from 3.23 GiB to
8.43 GiB RSS over 150.5 s and `dmesg` recorded an OOM kill with about
8.47 GiB anonymous RSS.  Normal attempts in that campaign stayed around
3.3--3.5 GiB.

The map input path was therefore changed without touching safety policy.  The
DDS cloud callback now validates and enqueues only the latest immutable ROS
message.  One dedicated worker performs PCL conversion, ROG-Map update,
copy-on-write snapshot publication and process ACK.  Pending input is bounded
to one latest frame, and shutdown clears it and joins the worker.  This keeps
heavy allocation on one allocator/thread arena and prevents a planner stall
from moving successive map allocations across executor threads.

Focused map10 Full n=3 and Adaptive n=3 both completed 3/3 first-attempt,
static-contact-free and without retry/OOM.  Full peak RSS was at most
3,236.6 MiB and Adaptive at most 3,232.8 MiB.  Only after those two gates was
the fresh 300-run campaign started.  The two partial pre-fix files are not
pooled with the final result.

Focused raw data:

- `results/map5_full_goal_fallback_n3_raw_20260828.csv`;
- `results/map5_full_goal_fallback_n5_raw_20260828.csv`;
- `results/map_worker_seed10_full_n3_raw_20260828.csv`; and
- `results/map_worker_seed10_adaptive_n3_raw_20260828.csv`.

The two diagnostic pre-fix partial campaigns are
`results/counterbalanced_candidate_3mode_seed1_10_n10_raw_20260828.csv` and
`results/counterbalanced_candidate_3mode_seed1_10_n10_goal_fallback_raw_20260828.csv`.

### Final fresh n=10 result

The corrected-binary campaign completed 300/300 rows with process exit code
0.  Every row was first-attempt, run-valid, speed-valid and backed by the
source static PCD.  Full and Adaptive each completed and were safety-qualified
100/100.  Fixed Sector completed 100/100 but was safety-qualified 94/100:
maps7, 8 and 9 each had two distinct static-PCD body intersections.  Adaptive
was safe in every matching map/run block.

`safe` means completion plus run/speed validity and zero static-PCD body
intersection.  `static events` is the authoritative source-PCD episode count;
legacy rendered-cloud diagnostics remain separate in the raw CSV.

| map | Full complete/safe | Sector complete/safe · static events | Adaptive complete/safe | mean time F/S/A (s) | Adaptive effective opens |
|---:|:---:|:---:|:---:|---:|---:|
| 1 | 10/10 | 10/10 · 0 | 10/10 | 60.45 / 59.92 / 60.84 | 170 |
| 2 | 10/10 | 10/10 · 0 | 10/10 | 56.37 / 57.15 / 59.47 | 181 |
| 3 | 10/10 | 10/10 · 0 | 10/10 | 67.17 / 62.73 / 66.64 | 135 |
| 4 | 10/10 | 10/10 · 0 | 10/10 | 69.26 / 69.56 / 70.94 | 116 |
| 5 | 10/10 | 10/10 · 0 | 10/10 | 66.65 / 67.05 / 73.85 | 104 |
| 6 | 10/10 | 10/10 · 0 | 10/10 | 71.18 / 73.13 / 75.84 | 120 |
| 7 | 10/10 | 10/8 · 2 | 10/10 | 80.28 / 76.14 / 76.72 | 88 |
| 8 | 10/10 | 10/8 · 2 | 10/10 | 74.08 / 72.51 / 82.53 | 63 |
| 9 | 10/10 | 10/8 · 2 | 10/10 | 80.48 / 82.66 / 89.15 | 97 |
| 10 | 10/10 | 10/10 · 0 | 10/10 | 90.21 / 79.63 / 87.35 | 86 |
| **total/mean** | **100/100** | **100/94 · 6** | **100/100** | **71.61 / 70.05 / 74.33** | **1,160** |

Sector collision rows were map7 runs5/9, map8 runs2/8 and map9 runs1/5.
Their minimum source-PCD clearances ranged from -0.011 to -0.189 m.  The
cohort therefore shows the intended distinction: fixed angular cropping kept
mission completion but lost physical safety in six trials, while Adaptive
recovered all six without reverting to Full's continuous workload.

### Map-labelled computation, update frequency and payload

All values below are per-run means.  Triplets are Full/Sector/Adaptive.
Payload is processed ROG-Map application payload, not NIC, wireless or DDS
wire bandwidth.

| map | points/update F/S/A | total/update F/S/A (ms) | processed payload F/S/A (Mbit/s) | map updates F/S/A (Hz) | FSM CPU F/S/A (%) |
|---:|---:|---:|---:|---:|---:|
| 1 | 15,533 / 7,123 / 12,406 | 31.70 / 11.36 / 22.32 | 32.07 / 8.94 / 11.58 | 8.07 / 7.84 / 5.02 | 117.63 / 97.10 / 98.06 |
| 2 | 15,737 / 6,820 / 12,282 | 32.18 / 11.55 / 23.25 | 32.25 / 8.56 / 11.30 | 7.99 / 7.84 / 4.91 | 118.24 / 99.38 / 98.23 |
| 3 | 22,847 / 10,491 / 18,421 | 37.46 / 13.57 / 29.23 | 35.28 / 10.25 / 15.44 | 6.02 / 6.10 / 4.26 | 101.24 / 90.53 / 88.62 |
| 4 | 24,220 / 12,266 / 20,529 | 36.24 / 13.33 / 29.25 | 37.86 / 11.17 / 16.84 | 6.11 / 5.69 / 4.11 | 101.91 / 83.75 / 84.64 |
| 5 | 27,330 / 13,323 / 22,922 | 40.88 / 14.53 / 32.17 | 44.61 / 12.60 / 18.45 | 6.38 / 5.91 / 4.00 | 108.31 / 85.06 / 84.29 |
| 6 | 30,497 / 14,796 / 25,125 | 38.75 / 13.83 / 30.90 | 46.51 / 13.14 / 19.95 | 5.95 / 5.54 / 3.98 | 103.76 / 82.23 / 83.89 |
| 7 | 36,458 / 19,557 / 31,036 | 38.16 / 14.50 / 31.71 | 47.92 / 16.68 / 24.21 | 5.14 / 5.32 / 3.91 | 88.56 / 79.54 / 80.95 |
| 8 | 34,110 / 18,070 / 28,419 | 40.07 / 14.62 / 32.67 | 46.28 / 15.90 / 20.96 | 5.29 / 5.51 / 3.62 | 91.51 / 81.71 / 71.47 |
| 9 | 43,545 / 24,346 / 36,797 | 37.28 / 13.90 / 30.23 | 63.60 / 20.95 / 27.83 | 5.70 / 5.38 / 3.73 | 98.49 / 77.25 / 74.39 |
| 10 | 41,913 / 23,689 / 35,518 | 35.94 / 14.23 / 30.89 | 54.66 / 21.21 / 27.17 | 5.09 / 5.58 / 3.78 | 85.90 / 80.13 / 77.88 |

The mode-level run means and changes from Full are:

| metric | Full | Sector | Adaptive | Sector vs Full | Adaptive vs Full |
|:---|---:|---:|---:|---:|---:|
| mission time (s) | 71.61 | 70.05 | 74.33 | -2.19% | +3.80% |
| map updates (Hz) | 6.173 | 6.071 | 4.131 | -1.66% | -33.08% |
| points/update | 29,219 | 15,048 | 24,346 | -48.50% | -16.68% |
| map total/update (ms) | 36.866 | 13.544 | 29.260 | -63.26% | -20.63% |
| occupancy update (ms) | 13.193 | 4.730 | 11.471 | -64.15% | -13.05% |
| processed payload (Mbit/s) | 44.104 | 13.941 | 19.372 | -68.39% | -56.08% |
| FSM CPU (%) | 101.56 | 85.67 | 84.24 | -15.64% | -17.05% |
| effective full-view opens | 0 | 0 | 1,160 | - | 11.60/run |

Update-weighted aggregation gives the same conclusion: Adaptive versus Full
reduced points/update 15.47%, total/update 20.36% and occupancy update time
12.75%.  Adaptive's 2.72 s mean mission-time cost is concentrated most visibly
on maps5, 8 and 9.  It comes with bounded full-view/ACK/replan recovery cycles;
CPU and map traffic still fall because the expensive full view is not held
continuously.

Accepted Sector and Adaptive filter rows processed every accepted callback
(43,628/43,628 and 44,776/44,776) with worker overwrite 0, so the reduction is
not explained by silently dropping input.  All final rows ended with no ACK
timeout, retry, supersede, abandon or pending trajectory-guard generation.

### Pairing, memory and claim boundary for n=10

Continuous global order rotation placed Full/Sector/Adaptive in each of the
three order positions 33 or 34 times.  In matched safety-qualified blocks,
Full versus Sector discordance was 6:0 and Sector versus Adaptive was 0:6;
the exact two-sided McNemar value is `p=0.03125` for each.  Full versus
Adaptive had no discordance (`p=1.0`).  This is stronger evidence than the
earlier fixed-order n=3 gate, but remains a single map family and simulator
cohort.

The final 300 rows had retry 0 and OOM 0.  Maximum FSM RSS was 3,263.95 MiB,
minimum host available memory was 3,862.91 MiB and sampled memory-PSI avg10
was zero.  Host swap was already almost full and peaked near 2,048 MiB, but
the pre-fix 8.43 GiB growth did not recur.  The exact formerly failing map10
run3 Full block completed first-attempt.

The final raw file is
`results/counterbalanced_map_worker_3mode_seed1_10_n10_raw_20260828.csv`.
For 100/100, the 95% Wilson lower bound is 96.30%; for Sector 94/100 it is
87.52%.  Consequently this cohort supports observed 100% Full/Adaptive
completion and static-map safety, not population-level 100%, formal collision
freedom, unseen-map generalization or hardware readiness.

## Claim boundary

Do not claim population 100%, formal collision freedom, unseen-map
generalization or hardware readiness.  Keep completion, source-PCD safety and
live-render markers as separate outcomes.  `obs_skip_num` remains a no-op in
the relevant path; NaN/clearance-penalty defects, BackupTrajOpt coverage and
the `DRONE_R=robot_r` zero-margin limitation are not solved by this work.
