# Static blind-fork burst-dropout held-out confirmation result

Date: 2026-09-10 (Asia/Seoul)

Decision: **`CONFIRMATORY_TRANSFER_OBSERVED` for the preregistered finite
three-map, ten-phase, simulation-only stress suite.** This is not a
population-level 100% guarantee and is not normal Map1--10 efficiency
evidence.

## Question and frozen scope

The earlier `shm1_h9` result was exploratory and used a uniform 2 Hz sensor.
Before generating the present assets or observing any flight, three held-out
static topology variants and a bounded fault schedule were frozen in
`docs/static_burst_dropout_confirmation_preregistration_20260910.md`.

The renderer remained at 10 Hz. After a 1.0 s warm-up, sensor output was
suppressed for 0.5 s every 2.0 s. Run indices 1--10 used paired phases
0.0, 0.2, ..., 1.8 s. Rendering and dynamics continued during the loss. The
same mode-independent injector acted before DDS, direct Full handoff and the
filtered C++ frontend handoff. SUPER, v7 dynamics, the 45-degree fixed Sector,
1.5 m omnidirectional near-field bubble, Adaptive thresholds and all planner
and policy parameters were frozen.

The held-out maps were:

- C1 `shc1_mirror_hazard`: horizontal reflection of the developed fork;
- C2 `shc2_wide_offset_hazard`: wider corridor and shifted divider; and
- C3 `shc3_near_short_hazard`: nearer closure and shorter offset divider.

Each scene contains continuous static background, a direct branch closed by a
static wall and a distinct inflation-feasible bypass. No dynamic obstacle was
used.

## Implementation and prerequisite gates

A default-off simulator fault injector records configured/observed phase,
rendered/delivered/dropped frames, burst count, maximum consecutive loss and
maximum delivered-frame gap. `SUPER_SENSOR_BURST_DROPOUT_PHASE_S` changes only
the registered per-run phase. Ordinary configurations retain the original
default-off behavior.

The production replay witness was extended with a paired mode: one actual
MARSIM-rendered stream is handed to both the production Sector and Adaptive
C++ frontends. A frame-stream FNV-1a hash makes equal raw input an explicit
gate instead of an assumption. The three paired replay gates all passed:

| Map | Raw conflict/hazard frames | Raw stream hash equal | Sector retained conflict/hazard | Adaptive consecutive fresh `OCCUPIED` | Adaptive minimum distance (m) |
|---|---:|---:|---:|---:|---:|
| C1 | 10/10 | yes | 0/0 | 5 | 0.1515 |
| C2 | 10/10 | yes | 0/0 | 6 | 0.1848 |
| C3 | 10/10 | yes | 0/0 | 5 | 0.1674 |

Actual-PCD structure gates also passed for all maps. Their direct-route body
clearances were -0.1898/-0.1879/-0.1920 m, their body-fixed initial Sector
contained zero closure samples, and the velocity-aligned Sector contained
7,801/8,214/6,761 samples. The inflated bypass was present in every map.

The default-off/configured fault smoke passed. The staged Full feasibility
flight then completed safely on the first attempt for all three maps, with
times 7.28/5.57/6.12 s and clearances 0.748/0.504/0.350 m. The paired run-1
smoke was retained without selecting maps by outcome: Sector contacted in C1
and C2 but was safe in C3, while Adaptive was safe in all three. All maps
therefore proceeded to the frozen matrix.

## Frozen matrix result: n=10 per mode and map

The 90 rows are new rotating-order runs; gate and smoke rows are not pooled.
Safe completion means mission completion with zero static-PCD contact.

| Map | Mode | Completion | Contact runs | Safe completion | Mean time (s) | Mean clearance (m) |
|---|---|---:|---:|---:|---:|---:|
| C1 mirror | Full | 10/10 | 0/10 | **10/10** | 6.735 | 0.536 |
|  | Fixed Sector | 9/10 | **6/10** | **4/10** | 19.912 | 0.025 |
|  | Adaptive | 10/10 | 0/10 | **10/10** | 6.885 | 0.450 |
| C2 wide-offset | Full | 10/10 | 0/10 | **10/10** | 6.370 | 0.428 |
|  | Fixed Sector | 10/10 | **6/10** | **4/10** | 17.713 | 0.066 |
|  | Adaptive | 10/10 | 0/10 | **10/10** | 6.942 | 0.390 |
| C3 near-short | Full | 10/10 | 0/10 | **10/10** | 6.481 | 0.425 |
|  | Fixed Sector | 10/10 | **5/10** | **5/10** | 10.540 | 0.084 |
|  | Adaptive | 10/10 | 0/10 | **10/10** | 7.098 | 0.484 |
| **Aggregate** | **Full** | **30/30** | **0/30** | **30/30** | **6.529** | **0.463** |
|  | **Fixed Sector** | **29/30** | **17/30** | **13/30** | **16.055** | **0.058** |
|  | **Adaptive** | **30/30** | **0/30** | **30/30** | **6.975** | **0.442** |

C1 run 3 was a valid outcome rather than infrastructure loss: it contacted at
-0.186 m clearance and did not finish before the 60 s timeout. Every other
Sector contact completed. Contact phases were distributed across the frozen
grid rather than arising from one selected phase: C1 had six, C2 six and C3
five contact phases.

The paired Adaptive-versus-Sector discordance was 17 runs where Sector was
unsafe and Adaptive was safe, versus zero in the opposite direction. The
preregistered aggregate exact two-sided McNemar p-value is
`1.52587890625e-05`. Per-map p-values are 0.03125, 0.03125 and 0.0625 for C1,
C2 and C3. The third map alone is not significant at 0.05; the preregistered
primary inference is the 30-pair aggregate, after reporting every map.

Wilson 95% safe-completion intervals are 0.8865..1.000 for aggregate Full and
Adaptive and 0.2738..0.6080 for Sector. For each individual 10/10 map the
lower bound is only 0.7225. Consequently, observed 30/30 is not evidence of a
population-level 100% guarantee.

## Computation, bandwidth and Adaptive activity

End-to-end cgroup CPU is the primary fair CPU comparison because it measures
simulator + frontend + planner + mission for every mode. Planner ingress is
the relevant bandwidth delivered to SUPER.

| Map | Mode | End-to-end CPU (cores) | Planner ingress (MiB/s) | Adaptive effective Full-open transitions/run |
|---|---|---:|---:|---:|
| C1 | Full | 0.971 | 10.621 | -- |
|  | Sector | 0.820 | 4.501 | 0.0 |
|  | Adaptive | 0.936 | 3.125 | 1.5 |
| C2 | Full | 0.977 | 11.002 | -- |
|  | Sector | 0.862 | 4.328 | 0.0 |
|  | Adaptive | 0.905 | 3.213 | 1.0 |
| C3 | Full | 0.975 | 11.361 | -- |
|  | Sector | 0.842 | 3.697 | 0.0 |
|  | Adaptive | 0.864 | 3.221 | 1.1 |
| **Aggregate** | **Full** | **0.974** | **10.995** | **--** |
|  | **Sector** | **0.841** | **4.175** | **0.0** |
|  | **Adaptive** | **0.902** | **3.187** | **1.2** |

Adaptive reduced mean end-to-end CPU by 7.44% and planner ingress by 71.02%
relative to Full in this suite. Per-map ingress reductions were 70.57%, 70.80%
and 71.65%. The secondary algorithm-scope number is a 31.07% reduction, but it
is not the primary result because the legacy Full composition includes the
simulator while the filtered-mode algorithm scope reports planner-only work.

Adaptive was effectively Full-open 54.24% of wall time, kept 38.22% of input
points, and issued means of 1.20 effective Full-open, 2.37 replan-guard and
1.13 trajectory-guard opening transitions per run. Exact fresh occupied audit
verdicts totalled 16 across 30 Adaptive rows: zero in C1 and eight each in C2
and C3. The correct causal description is therefore that the **deployed
Adaptive policy bundle**, including bounded Full refresh/replan/trajectory
guards, recovered Full-level observed safety. It would be incorrect to claim
that an exact-risk brake alone caused all 30 avoidances.

Adaptive mean flight time was 6.975 s versus Full's 6.529 s, a 0.446 s (6.83%)
cost. Sector's 16.055 s mean includes stopping/backtracking and the valid C1
timeout; low bandwidth alone was not sufficient for safety.

## Integrity and resource audit

All 90 rows used the registered phase, 10 Hz renderer, 1.0/2.0/0.5 s
warm-up/period/loss schedule, valid speed and static-PCD checks, and exactly one
attempt. Observed cadence was 9.995..10.101 Hz, consecutive losses 4..6 frames
and delivered-frame gaps 0.503..0.703 s. There were no retries,
infrastructure failures, resource aborts or cgroup OOM kills.

The host did experience late-campaign memory/swap pressure: per-row minimum
available memory reached 5,211 MiB, host swap peaked near 2,048 MiB and memory
PSI reached 0.18 in two rows. The preflight guard delayed launches until its
7,168 MiB condition was met; all retained rows remained resource-valid. This
means the campaign was not invalidated, but future long campaigns should
retain the guard and run on a cleaner host when measuring small CPU effects.

## Supported claim and remaining limit

The supported claim is: across three preregistered held-out static blind-fork
geometries and ten paired phases of bounded 10 Hz burst loss, Full and
Adaptive were safe in all 30 observed runs, Fixed Sector was unsafe in 17,
the paired aggregate favoured Adaptive, and Adaptive substantially reduced
planner ingress relative to Full.

This suite remains finite, simulation-only and deliberately stressful. It
does not prove all-map or real-world safety, deterministic 100% completion,
or nominal-condition efficiency. Normal Map1--10 results remain the primary
efficiency evidence. The next independent evidence, if required for a paper,
is PX4 SITL/realistic dynamics or actual LiDAR/rosbag replay with the same
fault contract; this held-out suite must not be tuned after its result.

Primary machine-readable evidence:

- `docs/static_burst_dropout_confirmation_preregistration_20260910.md`
- `results/static_burst_dropout_structure_gate_20260910.json`
- `results/static_burst_dropout_fault_integrity_20260910.json`
- `results/static_burst_dropout_c1_mirror_paired_replay_gate_20260910.json`
- `results/static_burst_dropout_c2_wide_offset_paired_replay_gate_20260910.json`
- `results/static_burst_dropout_c3_near_short_paired_replay_gate_20260910.json`
- `results/static_burst_dropout_full_gate_n1_raw_20260910.csv`
- `results/static_burst_dropout_paired_smoke_n1_raw_20260910.csv`
- `results/static_burst_dropout_confirmation_three_mode_n10_raw_20260910.csv`
- `results/static_burst_dropout_confirmation_three_mode_n10_result_20260910.json`
