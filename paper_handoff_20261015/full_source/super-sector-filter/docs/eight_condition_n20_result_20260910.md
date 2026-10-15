# Eight-condition n=20 paper-table result

> [!NOTE]
> This frozen eight-condition result remains unchanged. A separately
> preregistered C4--C5 prospective extension has since produced the current
> ten-condition, 600-row table. Use
> `docs/ten_condition_n20_result_20260910.md` for the latest result and retain
> this document as the immutable pre-extension record.

Date: 2026-09-10 (Asia/Seoul)

Decision: **`EIGHT_CONDITION_N20_COMPLETE`** and independent stress block
decision **`STRESS_REPLICATION_OBSERVED`**.

This result follows the extension frozen in
`docs/eight_condition_n20_extension_preregistration_20260910.md`. No planner,
policy, map, dynamics, threshold or outcome rule was changed during the new
flights. The result contains 480 quality-valid table rows: 300 existing
normal-rate rows and 180 static burst-dropout rows.

## What the eight conditions mean

The table has eight **reporting conditions**, not eight single physical maps.
The five normal radius tiers retain both random-layout replicates instead of
discarding one member of each pair. Each tier therefore contains two maps by
ten runs, or 20 observations per mode. The three stress conditions contain
one held-out geometry each and two separately reported ten-run phase blocks.

| Condition | Physical map(s) | Repetition structure | Family |
|---|---|---|---|
| R1 | `seed1`, `seed2` | 2 layouts x 10 | normal, radius 0.150 m |
| R2 | `seed3`, `seed4` | 2 layouts x 10 | normal, radius 0.275 m |
| R3 | `seed5`, `seed6` | 2 layouts x 10 | normal, radius 0.400 m |
| R4 | `seed7`, `seed8` | 2 layouts x 10 | normal, radius 0.525 m |
| R5 | `seed9`, `seed10` | 2 layouts x 10 | normal, radius 0.650 m |
| C1 | `shc1_mirror_hazard` | block 1 n=10 + block 2 n=10 | burst-dropout mirror |
| C2 | `shc2_wide_offset_hazard` | block 1 n=10 + block 2 n=10 | burst-dropout wide-offset |
| C3 | `shc3_near_short_hazard` | block 1 n=10 + block 2 n=10 | burst-dropout near-short |

Normal and stress results are not pooled into a single success, time, CPU or
bandwidth result because their missions and sensor conditions differ.

## Condition-level safety and completion

Safe completion means mission completion and zero authoritative static-PCD
contact. Mean time includes every retained row, including unsafe completion
and valid 60 s timeout rows.

| Condition | Full safe / contact / mean s | Fixed Sector safe / contact / mean s | Adaptive safe / contact / mean s | Adaptive effective Full-open transitions/run |
|---|---:|---:|---:|---:|
| R1 | 20/20 / 0 / 57.749 | 20/20 / 0 / 56.982 | 20/20 / 0 / 56.713 | 21.05 |
| R2 | 20/20 / 0 / 58.171 | 20/20 / 0 / 57.635 | 20/20 / 0 / 56.650 | 20.30 |
| R3 | 20/20 / 0 / 60.438 | 20/20 / 0 / 59.150 | 20/20 / 0 / 59.482 | 21.70 |
| R4 | 20/20 / 0 / 63.449 | 20/20 / 0 / 62.267 | 20/20 / 0 / 61.851 | 21.45 |
| R5 | 20/20 / 0 / 71.514 | 19/20 / 1 / 70.584 | 20/20 / 0 / 71.197 | 18.90 |
| C1 | 20/20 / 0 / 6.744 | 7/20 / 13 / 14.799 | 20/20 / 0 / 6.904 | 1.50 |
| C2 | 20/20 / 0 / 6.370 | 9/20 / 11 / 17.132 | 20/20 / 0 / 6.748 | 1.05 |
| C3 | 20/20 / 0 / 6.400 | 11/20 / 9 / 10.826 | 20/20 / 0 / 6.897 | 1.15 |

All Full and Adaptive cells were observed at 20/20 safe completion. Their
per-condition Wilson 95% lower bound is nevertheless only 0.8389, so these
observations are not a population-level 100% guarantee. In the normal family,
Full and Adaptive were 100/100 safe and Fixed Sector was 99/100 safe. The one
normal Sector contact was in the R5 `seed9`/`seed10` tier.

The stress family gave Full 60/60, Adaptive 60/60 and Sector 27/60 safe
completions. Full and Adaptive have a combined stress Wilson 95% interval of
0.9398..1.000; Sector's interval is 0.3309..0.5751. Fixed Sector completed
58/60 missions but had 33 contact runs, demonstrating why completion alone is
not the safety endpoint.

## Independent block-2 replication

Block 2 was frozen after block-1 outcomes and before any run-11--20 flight.
It repeated the paired phase grid 0.0..1.8 s without replacing block 1.

| Map | Block | Full safe | Sector safe | Sector contact | Adaptive safe |
|---|---|---:|---:|---:|---:|
| C1 | 1 | 10/10 | 4/10 | 6/10 | 10/10 |
| C1 | 2 | 10/10 | 3/10 | 7/10 | 10/10 |
| C2 | 1 | 10/10 | 4/10 | 6/10 | 10/10 |
| C2 | 2 | 10/10 | 5/10 | 5/10 | 10/10 |
| C3 | 1 | 10/10 | 5/10 | 5/10 | 10/10 |
| C3 | 2 | 10/10 | 6/10 | 4/10 | 10/10 |
| **Aggregate** | **1** | **30/30** | **13/30** | **17/30** | **30/30** |
| **Aggregate** | **2** | **30/30** | **14/30** | **16/30** | **30/30** |

The preregistered block-2 paired discordance was 16 Sector-unsafe/
Adaptive-safe rows versus zero in the reverse direction. Exact two-sided
McNemar p=`3.0517578125e-05`. Every per-map condition also satisfied the
frozen requirement that Fixed Sector be unsafe at least once while Full and
Adaptive were 10/10 safe. Thus the new block independently reproduced the
original stress direction and passed every preregistered replication check.

For traceability, block 1 remains 17:0 with p=`1.52587890625e-05`. The combined
n=20 stress table is 33:0 with p=`2.3283064365386963e-10`, but this combined
test is secondary because the extension was selected after block-1 outcomes.
The combined per-condition p-values are 0.0002441, 0.0009766 and 0.0039063 for
C1, C2 and C3.

## Computation, bandwidth and switching

End-to-end cgroup CPU is the primary fair CPU measure because it includes the
same simulator, frontend, planner and mission scope for all modes. Planner
ingress is the bandwidth actually delivered to SUPER. Map compute is the
frontend/map processing time per frame and is complementary rather than a
substitute for end-to-end CPU.

| Family | Mode | Mean time (s) | End-to-end CPU (cores) | Planner ingress (MiB/s) | Map compute (ms/frame) | Effective Full-open/run |
|---|---|---:|---:|---:|---:|---:|
| Normal R1--R5 | Full | 62.264 | 1.508 | 9.577 | 32.574 | -- |
|  | Fixed Sector | 61.323 | 1.273 | 2.749 | 9.317 | 0.00 |
|  | Adaptive | 61.179 | 1.316 | 2.189 | 19.780 | 20.68 |
| Stress C1--C3 | Full | 6.504 | 0.966 | 10.983 | 23.979 | -- |
|  | Fixed Sector | 14.252 | 0.851 | 4.024 | 6.273 | 0.00 |
|  | Adaptive | 6.849 | 0.908 | 3.218 | 16.942 | 1.23 |

On normal R1--R5, Adaptive versus Full reduced planner ingress by 77.14%, map
compute by 39.28%, mean end-to-end CPU by 12.75% and end-to-end core-seconds
per mission by 14.45%. Mean mission time also fell by 1.74%. This is the
primary efficiency evidence.

On the deliberately faulty C1--C3 suite, Adaptive versus Full reduced planner
ingress by 70.70%, map compute by 29.35%, mean end-to-end CPU by 6.01% and
core-seconds by 2.12%, while mean mission time increased by 0.345 s (5.30%).
Adaptive was Full-open for 54.04% of stress wall time and retained 38.16% of
input points. It averaged 1.23 sustained effective Full-open, 2.40 replan-guard
and 1.13 trajectory-guard opening transitions per run.

Only 26 of 60 Adaptive stress rows contained an exact fresh `OCCUPIED` audit
verdict. Therefore the supported mechanism is the deployed Adaptive bundle of
bounded Full refresh, replan and trajectory guards; the result must not be
attributed to an exact-risk brake alone.

## Integrity and resource audit

The combined source has exactly 180 unique stress rows, and the first 90 are
byte-for-field identical to the frozen block-1 CSV. All 90 new rows were
unique first attempts with attempt count 1, retry count 0, valid speed,
resource, static-PCD and run gates, zero infrastructure failures and zero
cgroup OOM kills. Each of the ten phase values occurred exactly nine times
across the three maps and modes. The registered 10 Hz cadence and
1.0/2.0/0.5 s warm-up/period/loss checks passed for every row.

The host remained swap-heavy: block-2 peak swap was 2007.86 MiB and minimum
runtime available memory was 5842.50 MiB. The 7168 MiB preflight gate delayed
new launches when necessary. Memory PSI `some` and `full` maxima were both
zero in block 2, so no measured pressure stall or outcome retry occurred.

The analysis implementation passed all 83 native campaign tests. The result
file decision is `EIGHT_CONDITION_N20_COMPLETE`; all eight matrix, source,
copy, integrity and replication checks are true.

## Claim boundary

The defensible paper claim is that Adaptive retained Full-level **observed**
safety in five normal radius tiers and three static blind-fork burst-dropout
conditions, reproduced the stress advantage over a fixed 45-degree Sector in
an independently frozen second block, and reduced normal-condition planner
ingress and end-to-end CPU relative to Full.

This is still simulation-only. The normal tiers contain two deterministic
random layouts each, while each C condition repeats one geometry across two
phase-balanced run blocks; these are not 20 geometrically independent maps.
The dataset does not prove universal safety, real-world performance or a
population completion probability of 1.0. Normal and stress metrics must stay
separate in the paper.

Primary evidence:

- `docs/eight_condition_n20_extension_preregistration_20260910.md`
- `results/allmaps_stationary_conflict_deployed_resource_guard_three_mode_n10_raw_20260905.csv`
- `results/allmaps_stationary_conflict_deployed_resource_guard_three_mode_n10_validation.json`
- `results/static_burst_dropout_confirmation_three_mode_n10_raw_20260910.csv`
- `results/static_burst_dropout_extension_three_mode_n20_raw_20260910.csv`
- `results/eight_condition_n20_result_20260910.json`
- `results/static_burst_dropout_extension_block2_n10_artifacts_20260910/`

The extended stress CSV SHA-256 is
`7cc9bbaf238203bc8b9d0ec16dceb977a44fbb118dc41d5aabe7356cf30fad1a`.
The result JSON SHA-256 is
`f6c20e1a5ef4dffc3c6306c3c3a5f8eec7fb24aadb8c7647dbcf306702706c80`.
