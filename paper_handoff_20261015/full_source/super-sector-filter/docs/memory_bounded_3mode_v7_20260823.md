# Bounded memory and valid three-mode v7 regression (2026-08-23)

## Scope and validity

This follow-up addresses the memory/swap contamination reported in
`docs/native_cpp_timeout_recovery_v7_20260823.md`, adds an exact Adaptive
output-state transition counter, and runs a fresh Full/Sector/Adaptive smoke
cohort.

The final comparison uses `loop24.txt`, v=7, timeout 240 s, static PCD contact
monitoring, seeds 1-10, and one run per seed. Full uses
`static_seedmaps_guard_viability_tight_v7.yaml`, whose ROG-Map input is direct
`/cloud_registered`. Sector and Adaptive use
`static_seedmaps_guard_viability_tight_v7_filtered.yaml`, whose input is
`/cloud_sector`, with the native C++ strict-burst filter. All 30 rows have
`run_valid=true` and an active static-PCD monitor. Raw-cloud CIRI remains
default false and has no authority in these runs. Both final configs disable
detailed SFC-cloud logging and use the same 64-record bound, so logging cost is
not asymmetric between the direct and filtered arms.

An earlier diagnostic accidentally supplied the direct-Full YAML to Sector
and Adaptive. Their planner therefore consumed `/cloud_registered` and ignored
the filter output. Those rows are invalid as a three-mode comparison and are
not used below. The campaign runner now rejects a Sector/Adaptive override
unless its parsed `cloud_topic` is `/cloud_sector`. It also avoids launching an
unused pass-through filter for a direct Full override.

## Changes

### Replan-log memory is bounded

The previous campaign profile enabled `detailed_log_en`. Every replan record
then retained the complete point cloud used to construct its safe-flight
corridor, and `replan_logs_` grew until process shutdown. The fix:

- makes detailed point-cloud retention explicit and false by default;
- stores replan records in a deque capped by `detailed_log_max_entries` (64 by
  default), while separately reporting total and dropped record counts;
- always consumes the corridor generator's latest cloud by move, avoiding an
  extra copy and releasing producer high-water capacity;
- excludes the SFC cloud from normal campaign records while retaining scalar,
  trajectory, return-code, and timing fields; and
- clears the large cloud capacity when a reusable `LogOneReplan` is reset.

The bounded log changes the semantics of saved binary debug logs: they contain
only the most recent capped window. A debugging experiment that needs the SFC
cloud must explicitly enable detailed logging and select a memory-safe cap.

### No-raycasting counters are sparse

The fixed-map profile has `raycasting_en=false`, but ROG-Map still allocated
two map-sized `uint16_t` arrays (`operation_cnt` and `hit_cnt`). For the
491 x 491 x 981 configured grid, this reserves about 0.88 GiB even though one
scan touches only a small subset of cells.

The no-raycasting path now uses a per-batch `unordered_map` keyed by voxel hash
and erases entries as the update cache is committed. The existing dense-vector
path is preserved unchanged when full raycasting is enabled. The prior
same-scan duplicate-hit coalescing is preserved in the sparse path.

### Runner evidence and configuration guard

`native_campaign.py` now keeps attempt-specific stack/filter/monitor/memory
artifacts and records attempt count, retry reasons, cgroup OOM-kill delta, FSM
RSS/PSS/swap, host available memory/swap, cgroup memory/swap, and memory PSI.
This distinguishes a mission failure from an infrastructure retry and prevents
a successful retry from overwriting the failed attempt's evidence.

### Exact Adaptive transitions

The C++ filter now counts transitions of the actual combined output state:

`effective full-open = stall/recovery open OR replan-guard open`.

This count is intentionally distinct from component entry counters. A
persistent stall can generate repeated 0.6 s open / 1.4 s closed pulses while
remaining inside one recovery episode, and overlapping replan and stall causes
must not be double-counted. The final Adaptive cohort observed 321 effective
open transitions and 320 close transitions. Seed5 ended while open, which
explains the one-count difference.

### Stopped EXP `OCCUPIED` recovery

One invalid raw-input Adaptive diagnostic exposed a separate liveness loop:
`PlanFromRest` repeatedly rejected the outgoing EXP segment as `OCCUPIED`, but
the existing bounded topology recovery accepted only `CLEARANCE_MARGIN` as
geometric route-block evidence. A certified stopped EXP rejection with either
status can now arm the same bounded topology change. `MAP_STALE` and
`UNOBSERVED` remain excluded, and moving-state behavior is unchanged.

Post-change targeted seed6/10 diagnostics completed without contact, but the
rare `OCCUPIED` branch did not reoccur. Therefore this branch is implemented
and build-tested, not execution-proven by the final valid cohort, and it must
not be credited for that cohort's result.

## Memory progression

| Stage | Scope | Completion | Peak FSM RSS | FSM swap | Retry / OOM delta | Interpretation |
|---|---:|---:|---:|---:|---:|---|
| Unbounded detailed log | failing Full seed5 attempt | failed | about 7.09 GiB before kill | host swap exhausted | kernel OOM kill | original failure evidence |
| Bounded log, dense counters | seed6/10 x 3, three diagnostic labels | 18/18 | 4383.98 MiB | 0 MiB | 0 / 0 | growth fixed; mode labels are not a valid filter comparison |
| Sparse counters, Full | seed6/10 x 3 | 6/6 | 3472.67 MiB | 0 MiB | 0 / 0 | about 0.89 GiB below the dense-counter Full gate |
| Final valid three-mode cohort | seed1-10 x 1, 30 runs | 30/30 raw | 3455.69 MiB | 0 MiB | 0 / 0 | no recurring pressure in the measured FSM |

Across the final rows, peak FSM RSS ranged from 3279.85 to 3455.69 MiB and peak
FSM PSS was 3432.76 MiB. One Sector seed1 sample observed a brief host-wide
memory PSI `some/full avg10` value of 0.18; every other final row was 0.
The host still reported nearly 2 GiB total swap in use and the cgroup retained
about 1489 MiB swap from the surrounding environment, but the measured FSM
itself used 0 MiB swap. With no FSM swap, retry, or OOM increment, the isolated
PSI sample and host-wide occupied swap do not reproduce the earlier sustained
FSM pressure.

## Final aggregate results

| Mode | Raw complete | Safe complete | Contact runs / events | Worst body clearance | Mean / max time | Retained input | Effective open / close |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 10/10 | 10/10 | 0 / 0 | +0.208 m | 73.87 / 91.27 s | 100.00% | 0 / 0 |
| Sector | 10/10 | 9/10 | 1 / 2 | -0.007 m | 77.30 / 102.42 s | 51.20% | 0 / 0 |
| Adaptive | 10/10 | 10/10 | 0 / 0 | +0.216 m | 90.41 / 136.18 s | 47.20% | 321 / 320 |

Sector seed7 completed the waypoint loop but crossed the static body-contact
threshold, so raw completion and safety-qualified completion must not be
conflated. Adaptive removed the observed Sector contact in this small cohort,
but took 16.96% more wall time than Sector and 22.39% more than Full.

## Per-seed safety, time, and Adaptive transitions

| Seed | Full safe / time / clr | Sector safe / time / clr | Adaptive safe / time / clr | Adaptive open / close | Open duty | Retained input |
|---:|---|---|---|---:|---:|---:|
| 1 | yes / 56.26 s / +0.266 | yes / 51.72 s / +0.332 | yes / 71.29 s / +0.254 | 26 / 26 | 20.21% | 41.31% |
| 2 | yes / 58.84 s / +0.307 | yes / 54.46 s / +0.295 | yes / 59.26 s / +0.303 | 23 / 23 | 22.31% | 37.69% |
| 3 | yes / 66.66 s / +0.283 | yes / 66.38 s / +0.264 | yes / 76.92 s / +0.275 | 34 / 34 | 28.36% | 47.74% |
| 4 | yes / 65.71 s / +0.266 | yes / 79.76 s / +0.180 | yes / 66.76 s / +0.216 | 26 / 26 | 21.67% | 36.06% |
| 5 | yes / 74.10 s / +0.208 | yes / 76.42 s / +0.225 | yes / 83.23 s / +0.255 | 32 / 31 | 26.60% | 47.42% |
| 6 | yes / 83.44 s / +0.285 | yes / 89.30 s / +0.293 | yes / 90.83 s / +0.305 | 28 / 28 | 17.43% | 43.93% |
| 7 | yes / 89.34 s / +0.274 | **no / 80.83 s / -0.007** | yes / 115.32 s / +0.243 | 36 / 36 | 24.05% | 48.21% |
| 8 | yes / 64.74 s / +0.277 | yes / 85.31 s / +0.219 | yes / 84.04 s / +0.285 | 26 / 26 | 17.92% | 44.69% |
| 9 | yes / 91.27 s / +0.294 | yes / 102.42 s / +0.230 | yes / 136.18 s / +0.229 | 45 / 45 | 22.60% | 56.48% |
| 10 | yes / 88.38 s / +0.214 | yes / 86.40 s / +0.236 | yes / 120.29 s / +0.268 | 45 / 45 | 29.89% | 52.28% |

Adaptive's time-weighted full-open duty was 23.38%. Its component counters were
7/2 stall-recovery entry/exit transitions and 248/248 replan-guard open/close
transitions. These are not additive substitutes for the 321/320 effective
output transitions for the reasons described above.

## Workload relative to Full

| Metric | Full | Sector | Sector reduction | Adaptive | Adaptive reduction |
|---|---:|---:|---:|---:|---:|
| Map commits | 5.400 Hz | 5.110 Hz | 5.37% | 3.233 Hz | 40.13% |
| Processed points/update | 28147.9 | 13682.2 | 51.39% | 20172.9 | 28.33% |
| Processed throughput | 151.99 kpts/s | 69.92 kpts/s | 54.00% | 65.22 kpts/s | 57.09% |
| Mapping time/update | 34.289 ms | 13.465 ms | 60.73% | 19.356 ms | 43.55% |
| Mapping work/mission | 13.678 s | 5.319 s | 61.12% | 5.658 s | 58.64% |
| FSM + filter CPU-work/mission | 64.143 s | 58.129 s | 9.38% | 57.897 s | 9.74% |
| Peak FSM RSS | 3455.69 MiB | 3314.16 MiB | 4.10% | 3396.14 MiB | 1.72% |

Adaptive processed 47.44% more points per update than fixed Sector because it
opens the full cloud when recovery evidence demands it, but its lower commit
rate made aggregate throughput 6.72% lower. Its mapping work per mission was
6.38% above Sector while recovering safety in the observed seed7 case.

The CPU-work values are useful smoke-scale observations after eliminating the
known memory growth, but these three arms ran sequentially with n=1 per seed
and without order crossing. They are not a clean population-level or hardware
performance guarantee.

## Speed and interpretation limits

The final fair rerun's sampled maxima were 7.004 m/s Full, 7.014 m/s Sector,
and 7.006 m/s Adaptive. A preliminary Adaptive row from the superseded
mixed-logging comparison had reported 9.842 m/s, but both a dedicated repeat
and the final fair seed3 rerun reported about 7.000 m/s. The preliminary value
is not part of the final table.

This is a sequential n=1 smoke cohort. It is not paired, no McNemar test is
reported, and 10/10 does not establish population-level 100% completion or
flight readiness. The result supports the intended descriptive pattern in
this sample: Full raw/static-safe 10/10, fixed Sector exposes a contact after
information cutting, and Adaptive restores the observed safety while reducing
map-side workload relative to Full.

Raw evidence:

- `results/memory_bounded_full_seed6_10_n3_raw_20260823.csv`
- `results/postopt_full_seed6_10_n3_raw_20260823.csv`
- `results/final_postopt_full_direct_seed1_10_n1_raw_20260823.csv`
- `results/final_postopt2_sector_filtered_seed1_10_n1_raw_20260823.csv`
- `results/final_postopt2_adaptive_filtered_seed1_10_n1_raw_20260823.csv`
- `results/final_postopt_3mode_n1_summary_20260823.csv`
- `results/final_postopt_3mode_seed_summary_20260823.csv`
