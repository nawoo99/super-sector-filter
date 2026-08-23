# Order-crossed Full/Sector/Adaptive v7 n=5 gate (2026-08-23)

## Scope and experiment validity

This is the clean broad follow-up requested after the bounded-memory n=1
smoke. It runs `loop24.txt` at v=7 with the static-PCD monitor, timeout 240 s,
seeds 1-10, five repetitions, and Full/Sector/Adaptive in a rotating order: 150
rows total. Full uses `static_seedmaps_guard_viability_tight_v7.yaml` and reads
`/cloud_registered` directly. Sector and Adaptive use
`static_seedmaps_guard_viability_tight_v7_filtered.yaml`, read
`/cloud_sector`, and use the native C++ `strict-burst` filter.

The runner was extended so a single interleaved campaign can route the direct
and filtered configs without accidentally giving Sector/Adaptive the Full
input. It rejects a Full config that does not use `/cloud_registered` and a
filtered config that does not use `/cloud_sector`. Rotation now continues
across seed boundaries, and every row records its global sequence number and
within-block order position. The resulting mode-position counts are the
closest possible balance: Full 17/16/17, Sector 17/17/16, and Adaptive
16/17/17 for positions 1/2/3.

All 150 rows have `run_valid=true`, an active static-PCD monitor, one attempt,
and a completed waypoint loop. The campaign took 231.9 minutes. Raw-cloud CIRI
remained default false and had no authority over flight decisions.

## Completion and contact result

`All-detector safe` means raw completion with zero unified contact events.
`Static safe` ignores a live-cloud-only threshold event but still requires the
static-PCD body clearance to remain non-negative.

| Mode | Raw complete | Static safe | All-detector safe | Contact runs / events | Worst static body clearance | Mean +/- SD / max time |
|---|---:|---:|---:|---:|---:|---:|
| Full | 50/50 | 49/50 | 49/50 | 1 / 2 | -0.146 m | 75.29 +/- 12.81 / 104.87 s |
| Sector | 50/50 | 48/50 | 47/50 | 3 / 6 | -0.027 m | 80.83 +/- 18.42 / 134.32 s |
| Adaptive | 50/50 | 50/50 | 50/50 | 0 / 0 | +0.141 m | 92.12 +/- 23.35 / 141.55 s |

The intended descriptive ordering appears in this sample: fixed Sector loses
safety after information cutting, while Adaptive restores all 50 observed
runs and still reduces map-side work. The stronger project target is not yet
met, however, because Full itself has one measured contact. Raw completion
must not be reported as collision-free completion.

### Contact forensics

| Sequence | Run | Order | Detector evidence | First contact | Interpretation |
|---:|---|---:|---|---|---|
| 91 | seed7 r1 Full | 1 | static + live, 2 events | 4.292 s, 0.228 m/s, `(11.950,12.845,1.049)` | stopped endpoint inside obstacle envelope |
| 108 | seed8 r1 Sector | 3 | live only, 1 event | 13.253 s, 6.523 m/s, center distance 0.194 m | 6 mm live-cloud body overlap; static voxel PCD reported +0.042 m |
| 139 | seed10 r2 Sector | 1 | live + static, 2 events | 118.608 s, 7.000 m/s | high-speed sector miss; static body clearance -0.007 m |
| 146 | seed10 r4 Sector | 2 | live + static, 3 events | 16.765 s, 6.881 m/s | two live episodes; later static body clearance -0.027 m |

The Full contact is not an initial-spawn artifact. Immediately before it,
generation 7 was repeatedly certified `SAFE` while ending at approximately
`[11.950, 12.850, 1.050]`. CIRI simultaneously warned that its corridor was
infeasible with only 0.0179 m obstacle distance. Two very short `no_backup`
tails were then committed as safe, the trajectory finished at that endpoint,
and both static and live clouds confirmed contact. Later topology rerouting
recovered mission liveness, but it could not undo the already-entered contact.

This identifies a narrower remaining Full defect: certification of a short
remaining tail/hold does not enforce a hard clearance invariant on the current
and terminal stop pose. It is different from the previously fixed repeated
same-topology and stopped A* timeout loops. The next safety change should make
current-pose and terminal-pose clearance explicit preconditions for accepting
a tail or certified stationary hold, and must reject/brake early enough that
the vehicle stops before entering the body envelope. Simply rerouting after
the endpoint is already in contact is too late.

## Per-seed result and Adaptive transitions

Each safety cell is all-detector-safe runs out of five. Times are per-mode
means. Adaptive transition counts are exact edges of the combined output state
`stall/recovery open OR replan-guard open`.

| Seed | Full safe / mean time | Sector safe / mean time | Adaptive safe / mean time | Adaptive open / close | Open duty | Retained input |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5/5 / 58.20 s | 5/5 / 59.43 s | 5/5 / 63.27 s | 121 / 121 | 21.69% | 38.92% |
| 2 | 5/5 / 57.05 s | 5/5 / 58.63 s | 5/5 / 61.63 s | 118 / 118 | 21.49% | 39.74% |
| 3 | 5/5 / 68.25 s | 5/5 / 67.87 s | 5/5 / 79.31 s | 145 / 145 | 22.40% | 46.17% |
| 4 | 5/5 / 77.62 s | 5/5 / 78.20 s | 5/5 / 82.81 s | 113 / 113 | 17.57% | 47.13% |
| 5 | 5/5 / 74.13 s | 5/5 / 74.14 s | 5/5 / 91.67 s | 159 / 158 | 22.91% | 48.85% |
| 6 | 5/5 / 73.33 s | 5/5 / 90.37 s | 5/5 / 90.21 s | 154 / 153 | 22.01% | 49.81% |
| 7 | **4/5** / 85.81 s | 5/5 / 89.68 s | 5/5 / 111.07 s | 167 / 167 | 21.51% | 53.86% |
| 8 | 5/5 / 80.16 s | **4/5** / 79.08 s | 5/5 / 95.39 s | 152 / 151 | 21.95% | 50.40% |
| 9 | 5/5 / 90.10 s | 5/5 / 100.92 s | 5/5 / 122.80 s | 187 / 185 | 24.07% | 55.10% |
| 10 | 5/5 / 88.25 s | **3/5** / 109.93 s | 5/5 / 123.07 s | 202 / 201 | 26.08% | 55.03% |

Across all Adaptive rows there were **1518 effective full-open and 1512
full-close transitions**, or 30.36 +/- 9.81 opens per mission (range 19-62).
Six runs ended while open, explaining the six-edge difference. Time-weighted
full-open duty was 22.43%. Component counters were 36/13 stall-recovery
entry/exit and 1201/1201 replan-guard open/close; these must not be added to
the effective count because causes overlap and recovery episodes can pulse.

## Workload and frequency relative to Full

| Metric | Full | Sector | Sector reduction | Adaptive | Adaptive reduction |
|---|---:|---:|---:|---:|---:|
| Map commits | 5.466 Hz | 4.832 Hz | 11.60% | 2.944 Hz | 46.15% |
| Processed points/update | 28982.2 | 14157.2 | 51.15% | 19532.0 | 32.61% |
| Processed throughput | 158.43 kpts/s | 68.41 kpts/s | 56.82% | 57.50 kpts/s | 63.71% |
| Mapping time/update | 34.195 ms | 13.704 ms | 59.93% | 19.070 ms | 44.23% |
| Mapping work/mission | 14.074 s | 5.352 s | 61.97% | 5.172 s | 63.25% |
| FSM + filter CPU-work/mission | 66.069 s | 58.392 s | 11.62% | 55.411 s | 16.13% |
| Peak FSM RSS | 3474.36 MiB | 3428.75 MiB | 1.31% | 3415.11 MiB | 1.70% |
| Mean mission time | 75.29 s | 80.83 s | -7.35% | 92.12 s | -22.35% |

Adaptive processes 37.96% more points per update than fixed Sector when its
view opens, but commits 39.08% less often. Consequently its throughput is
15.95% below Sector and mapping work/mission is 3.38% below Sector, while its
mission takes 13.98% longer. Its combined CPU-work is 5.11% lower than Sector
in this order-crossed cohort. The result therefore supports the requested
map-work trade-off, but it also exposes an Adaptive mission-time cost.

## Order effect and paired safety check

| Mode | Position 1 safe | Position 2 safe | Position 3 safe |
|---|---:|---:|---:|
| Full | 16/17 | 16/16 | 17/17 |
| Sector | 16/17 | 16/17 | 15/16 |
| Adaptive | 16/16 | 17/17 | 17/17 |

Sector's three contact runs occurred once in each position. Full's one event
occurred in position 1. This does not support a single campaign-order cause,
although four total contact runs are too few to exclude smaller order effects.

Unlike the earlier sequential cohorts, these 50 seed/run blocks contain all
three modes with crossed order, so an exact paired McNemar calculation is
defined. Full versus Sector had 3 blocks where only Sector was unsafe and 1
where only Full was unsafe (two-sided exact p=0.625). Sector versus Adaptive
had 3 blocks where only Sector was unsafe (p=0.250). Full versus Adaptive had
1 block where only Full was unsafe (p=1.000). None is significant at 0.05;
the observed ordering is descriptive evidence, not a demonstrated population
difference.

## Memory and infrastructure

Every row used one attempt: retry 0, OOM-kill delta 0, FSM swap 0 MiB, and
memory PSI `some/full avg10` maximum 0. Peak FSM RSS/PSS was 3474.36/3451.11
MiB. Host-wide swap remained almost completely occupied at about 2048 MiB and
minimum available memory fell to 3351.88 MiB late in seed10, but the measured
FSM did not swap and there was no retry, OOM, or PSI response. Thus the old
unbounded per-run growth did not recur in this 150-run sequential gate.

## Statistical limit and next gate

The all-detector-safe rates are 98%, 94%, and 100%, with exact two-sided 95%
Clopper-Pearson intervals of 89.35-99.95%, 83.45-98.75%, and 92.89-100%.
Adaptive's 50/50 therefore does not prove population-level 100%; it only puts
the usual 95% two-sided lower bound at 92.89% for this test population.

The next implementation target is the Full seed7 endpoint/current-pose
certification hole, not more filter tuning. After adding a fail-closed terminal
clearance check, first run seed7 Full repeatedly with the same static/live
forensics, then rerun a crossed Full/Sector/Adaptive gate. Sector should remain
an intentionally degraded control; Adaptive must keep zero observed contact
and the Full-relative workload reduction. Raw-cloud CIRI remains default
false throughout.

Evidence files:

- `results/order_crossed_3mode_strict_v7_n5_raw_20260823.csv`
- `results/order_crossed_3mode_strict_v7_n5_summary_20260823.csv`
- `results/order_crossed_3mode_strict_v7_n5_seed_summary_20260823.csv`
- `results/order_crossed_3mode_strict_v7_n5_order_summary_20260823.csv`
