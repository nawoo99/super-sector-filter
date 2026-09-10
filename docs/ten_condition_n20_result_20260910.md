# Ten-condition n=20 paper-table result

Date: 2026-09-10 (Asia/Seoul)

Decision: **`TEN_CONDITION_N20_COMPLETE`**. The independently preregistered
C4--C5 prospective extension decision is
**`C4_C5_EXTENSION_OBSERVED`**.

This result extends, rather than replaces, the frozen eight-condition result.
No existing R1--R5 or C1--C3 row was rerun or edited. C4 and C5 were generated
and tested only after their geometry, gates, repetition count and decision
rules had been committed and pushed. Planner, v7 dynamics, 45-degree Fixed
Sector, Adaptive policy, common 10 Hz burst-dropout contract and safety
endpoint remained frozen.

## Reporting design

There are ten reporting conditions and 600 quality-valid table rows. A
condition contains 20 observations per mode, but the physical replication
structure differs and must remain explicit.

| Condition | Physical map(s) | Repetition structure | Family |
|---|---|---|---|
| R1 | `seed1`, `seed2` | 2 layouts x 10 | normal, radius 0.150 m |
| R2 | `seed3`, `seed4` | 2 layouts x 10 | normal, radius 0.275 m |
| R3 | `seed5`, `seed6` | 2 layouts x 10 | normal, radius 0.400 m |
| R4 | `seed7`, `seed8` | 2 layouts x 10 | normal, radius 0.525 m |
| R5 | `seed9`, `seed10` | 2 layouts x 10 | normal, radius 0.650 m |
| C1 | `shc1_mirror_hazard` | two frozen phase blocks, 10 + 10 | burst-dropout mirror |
| C2 | `shc2_wide_offset_hazard` | two frozen phase blocks, 10 + 10 | burst-dropout wide-offset |
| C3 | `shc3_near_short_hazard` | two frozen phase blocks, 10 + 10 | burst-dropout near-short |
| C4 | `shc4_deep_mirror_hazard` | prospective 20-run phase grid | burst-dropout deep mirror |
| C5 | `shc5_asymmetric_offset_hazard` | prospective 20-run phase grid | burst-dropout asymmetric offset |

R1--R5, C1--C3 and C4--C5 are reported separately. C1--C5 pooling is only a
secondary descriptive summary because C4/C5 were designed after C1--C3
outcomes were known.

## C4--C5 prerequisite gates

Both new maps passed every frozen gate before the 120-row matrix was started.

| Gate metric | C4 deep mirror | C5 asymmetric offset |
|---|---:|---:|
| Direct-route body clearance | -0.1854 m | -0.1861 m |
| Closure samples in initial body Sector | 0 | 0 |
| Closure samples in north-velocity Sector | 8,214 | 9,126 |
| Inflation-feasible bypass | yes | yes |
| Paired replay raw hazard/conflict frames | 10/10 | 10/10 |
| Sector filtered hazard/conflict points | 0/0 | 0/0 |
| Adaptive consecutive fresh `OCCUPIED` | 5 | 5 |
| Identical paired raw stream hash | pass | pass |
| Full gate safe completion / clearance | 1/1 / 0.406 m | 1/1 / 0.396 m |

The paired replay used the actual MARSIM renderer and production C++
frontend. It establishes that the registered surface was present in a common
raw stream, Fixed Sector removed it, and Adaptive's asynchronous risk frontend
detected the resulting path conflict.

## Condition-level outcome

Safe completion means mission completion and zero authoritative static-PCD
contact. Completion and contact are shown separately because an unsafe flight
can still reach the goal. Mean time includes all retained rows, including
valid 60 s timeouts.

| Condition | Full safe / complete / contact / mean s | Fixed Sector safe / complete / contact / mean s | Adaptive safe / complete / contact / mean s | Adaptive effective Full-open/run |
|---|---:|---:|---:|---:|
| R1 | 20/20 / 20/20 / 0 / 57.749 | 20/20 / 20/20 / 0 / 56.982 | 20/20 / 20/20 / 0 / 56.713 | 21.05 |
| R2 | 20/20 / 20/20 / 0 / 58.171 | 20/20 / 20/20 / 0 / 57.635 | 20/20 / 20/20 / 0 / 56.650 | 20.30 |
| R3 | 20/20 / 20/20 / 0 / 60.438 | 20/20 / 20/20 / 0 / 59.150 | 20/20 / 20/20 / 0 / 59.482 | 21.70 |
| R4 | 20/20 / 20/20 / 0 / 63.449 | 20/20 / 20/20 / 0 / 62.267 | 20/20 / 20/20 / 0 / 61.851 | 21.45 |
| R5 | 20/20 / 20/20 / 0 / 71.514 | 19/20 / 20/20 / 1 / 70.584 | 20/20 / 20/20 / 0 / 71.197 | 18.90 |
| C1 | 20/20 / 20/20 / 0 / 6.744 | 7/20 / 19/20 / 13 / 14.799 | 20/20 / 20/20 / 0 / 6.904 | 1.50 |
| C2 | 20/20 / 20/20 / 0 / 6.370 | 9/20 / 19/20 / 11 / 17.132 | 20/20 / 20/20 / 0 / 6.748 | 1.05 |
| C3 | 20/20 / 20/20 / 0 / 6.400 | 11/20 / 20/20 / 9 / 10.826 | 20/20 / 20/20 / 0 / 6.897 | 1.15 |
| C4 | 20/20 / 20/20 / 0 / 7.533 | 4/20 / 19/20 / 16 / 15.232 | 20/20 / 20/20 / 0 / 7.272 | 1.20 |
| C5 | 20/20 / 20/20 / 0 / 6.656 | 3/20 / 17/20 / 16 / 21.248 | 20/20 / 20/20 / 0 / 7.164 | 1.50 |

In the new C4--C5 extension, Full and Adaptive were each 40/40 safe while
Fixed Sector was 7/40 safe, completed 36/40, and contacted in 32/40 rows. The
paired discordance was 33 Sector-unsafe/Adaptive-safe versus zero in the
opposite direction; exact two-sided McNemar p=`2.3283064365386963e-10`.
C4 and C5 separately gave 16:0 (p=`3.0517578125e-05`) and 17:0
(p=`1.52587890625e-05`). Thus both physical-map extensions reproduce the
registered safety ordering rather than relying on one geometry.

Across C1--C5, the descriptive totals are Full 100/100 safe, Adaptive 100/100
safe and Sector 34/100 safe with 65 contact rows and six non-completions. The
66:0 combined paired result is descriptive, not a newly preregistered
confirmatory test. Full/Adaptive 100/100 has a Wilson 95% interval of
0.9630..1.0000 and therefore is not a population-level 100% guarantee.

## Computation, bandwidth and switching

End-to-end cgroup CPU is the primary fair CPU comparison because its scope is
simulator + frontend + planner + mission for every mode. Planner ingress is
the payload actually delivered to SUPER. `total_ms_mean` is map/frontend
compute per processed frame.

| Family | Mode | Mean time (s) | End-to-end CPU (cores) | Planner ingress (MiB/s) | Map compute (ms/frame) | Effective Full-open/run |
|---|---|---:|---:|---:|---:|---:|
| Normal R1--R5 | Full | 62.264 | 1.508 | 9.577 | 32.574 | -- |
|  | Fixed Sector | 61.323 | 1.273 | 2.749 | 9.317 | 0.00 |
|  | Adaptive | 61.179 | 1.316 | 2.189 | 19.780 | 20.68 |
| Prior stress C1--C3 | Full | 6.504 | 0.966 | 10.983 | 23.979 | -- |
|  | Fixed Sector | 14.252 | 0.851 | 4.024 | 6.273 | 0.00 |
|  | Adaptive | 6.849 | 0.908 | 3.218 | 16.942 | 1.23 |
| Prospective stress C4--C5 | Full | 7.094 | 0.969 | 11.202 | 23.382 | -- |
|  | Fixed Sector | 18.241 | 0.824 | 3.578 | 6.202 | 0.00 |
|  | Adaptive | 7.218 | 0.928 | 3.501 | 16.740 | 1.35 |

For C4--C5, Adaptive versus Full reduced planner ingress by 68.74%, map
compute by 28.41%, end-to-end CPU by 4.26%, and end-to-end core-seconds by
3.06%. Mean mission time increased by 0.123 s (1.74%). Adaptive retained
40.65% of input points and was Full-open for 52.93% of stress wall time. It
averaged 1.35 effective Full-open, 2.70 replan-guard and 1.125
trajectory-guard opening transitions per run.

Only 7/40 C4--C5 Adaptive rows contained any exact fresh `OCCUPIED` audit
verdict (16 verdicts total). The causal claim therefore remains the deployed
Adaptive bundle--bounded Full refresh plus replan and trajectory guards--not
an exact-risk brake in isolation.

The unchanged normal family remains the primary efficiency evidence:
Adaptive reduced planner ingress by 77.14%, map compute by 39.28%, end-to-end
CPU by 12.75% and core-seconds by 14.45% relative to Full, with 100/100
observed safe completions in both modes.

## Integrity and resource audit

The C4--C5 matrix contains exactly 120 unique rows. Every row was a first
attempt with attempt count 1, retry count 0, valid dropout phase/cadence,
speed, resource, static-PCD and run gates, no infrastructure failure and zero
cgroup OOM-kill delta. All 600 source rows passed the final matrix and source
hash checks.

The host remained swap-heavy during C4--C5: system peak swap use was
2048.00 MiB, minimum measured available memory was 5658.54 MiB, and the
largest measured campaign cgroup memory/swap values were 11441.04/1057.00
MiB. The 7168 MiB preflight gate delayed launches until its stable window was
met. Measured memory PSI `some` and `full` maxima were both zero, and there was
no resource retry or outcome replacement.

## Claim boundary and evidence

The supported claim is finite and simulation-only: across five normal radius
tiers and five static blind-fork burst-dropout conditions, Adaptive retained
Full-level observed safety; the separately preregistered C4--C5 extension
replicated Adaptive's safety advantage over a fixed 45-degree Sector while
retaining substantial bandwidth and compute reductions relative to Full.

This does not establish universal safety, real-world transfer, or a
population success probability of one. R tiers contain paired layouts, C1--C3
reuse one geometry over two phase blocks, and C4/C5 each repeat one physical
geometry. Normal and stress rates and efficiency metrics must not be pooled.

Primary evidence:

- `docs/static_burst_dropout_c4_c5_extension_preregistration_20260910.md`
- `results/static_burst_dropout_c4_c5_structure_gate_20260910.json`
- `results/static_burst_dropout_c4_deep_mirror_paired_replay_gate_20260910.json`
- `results/static_burst_dropout_c5_asymmetric_offset_paired_replay_gate_20260910.json`
- `results/static_burst_dropout_c4_c5_full_gate_n1_raw_20260910.csv`
- `results/static_burst_dropout_c4_c5_three_mode_n20_raw_20260910.csv`
- `results/ten_condition_n20_result_20260910.json`

C4--C5 campaign CSV SHA-256:
`34c8a7758a7cd6371ba6abb911600a1e80e9ad09c5c9dee3c9794645b3b8229e`.
Ten-condition result JSON SHA-256:
`16b923afe53ca5be1b7dd30c23b2b55c45efd32afaea34267ab3bdc9277c916d`.
