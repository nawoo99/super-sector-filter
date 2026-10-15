# Angular blind-turn v4 observed-exit gate result

Date: 2026-09-09 (Asia/Seoul)

## Decision

`abt4_observed_exit` removed the v3 empty-cloud/MAP_STALE confound, but it did
not produce the preregistered safety/mechanism separation. The Full-only row
passed, so the frozen three-mode n=3 pilot was run. Full, fixed Sector and
Adaptive all completed 3/3 without contact. Fixed Sector had no MAP_STALE row,
but also had zero target-turn degradation. Adaptive published 248 exact future-
trajectory verdicts across three rows, all FREE, and generated zero exact risk
brakes.

The frozen decision is `STOP_V4_THREE_MODE_GATE_FAILED`. No row was retried or
replaced and this map family will not be tuned into a held-out evaluation set.
This is a development gate, not a population estimate or McNemar test.

## Phase 1: Full-only feasibility

| Map | Mode | Complete | Contact | Time (s) | Waypoints | PCD clearance (m) | Hazard clearance (m) |
|---|---|---:|---:|---:|---:|---:|---:|
| `abt4_observed_exit` | Full | 1 | 0 | 14.06 | 2/2 | 0.324 | 0.323 |

The row was unique, first-attempt and run/resource/speed/performance/cgroup-
valid, with no retry, infrastructure failure, resource abort or OOM. It
therefore returned `PROCEED_TO_THREE_MODE_N3`.

## Phase 2: map-labelled pilot rows

| Map | Run | Mode | Complete | Contact | Time (s) | PCD clearance (m) | Hazard clearance (m) | Effective Full opens | Exact risk brakes |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| `abt4_observed_exit` | 1 | Full | 1 | 0 | 11.16 | 0.275 | 0.346 | — | 0 |
| `abt4_observed_exit` | 1 | Sector | 1 | 0 | 13.99 | 0.370 | 0.368 | 0 | 0 |
| `abt4_observed_exit` | 1 | Adaptive | 1 | 0 | 12.40 | 0.366 | 0.364 | 5 | 0 |
| `abt4_observed_exit` | 2 | Sector | 1 | 0 | 13.40 | 0.381 | 0.448 | 0 | 0 |
| `abt4_observed_exit` | 2 | Adaptive | 1 | 0 | 10.78 | 0.339 | 0.660 | 4 | 0 |
| `abt4_observed_exit` | 2 | Full | 1 | 0 | 13.90 | 0.254 | 0.251 | — | 0 |
| `abt4_observed_exit` | 3 | Adaptive | 1 | 0 | 13.37 | 0.199 | 0.195 | 4 | 0 |
| `abt4_observed_exit` | 3 | Full | 1 | 0 | 12.65 | 0.691 | 0.691 | — | 0 |
| `abt4_observed_exit` | 3 | Sector | 1 | 0 | 11.95 | 0.378 | 0.666 | 0 | 0 |

All nine rows were unique, first-attempt and quality-valid. Retry,
infrastructure failure, resource abort, OOM and contact counts were zero.

## Aggregate outcome and resource diagnostics

| Map | Mode | Safe completion | Mean time (s) | Mean PCD clearance (m) | Planner ingress (MiB/s) | Algorithm CPU (cores) | Map compute (ms/frame) | Peak RSS (MiB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `abt4_observed_exit` | Full | 3/3 | 12.57 | 0.407 | 5.091 | 1.123 | 16.324 | 3319.5 |
| `abt4_observed_exit` | Sector | 3/3 | 13.11 | 0.376 | 1.790 | 0.891 | 8.307 | 3143.9 |
| `abt4_observed_exit` | Adaptive | 3/3 | 12.18 | 0.301 | 1.302 | 0.902 | 11.467 | 3155.5 |

Against Full, Adaptive reduced planner ingress 74.42%, algorithm CPU 19.71%,
map compute time 29.75% and peak RSS 4.94%; mean mission time was 3.08% lower.
These n=3 resource differences are diagnostic, not inferential estimates.
Adaptive retained 35.234% of input points on average and opened Full 4.33 times
per row. The mean effective-open duty was 26.341%, of which 16.871 percentage
points were replan-guard open duty.

## What v4 established

The north observation wall did exactly what it was intended to do. All three
Sector rows retained non-empty observations after the turn and
`guard_main_pre_map_stale` was zero. The v3 Sector timeout therefore cannot be
used as evidence that the hidden cylinder made fixed Sector unsafe; it was an
empty-environment liveness artifact.

Once that artifact was removed, fixed Sector completed every row. The probe
was observed in all six filtered rows, but its centre was outside fixed Sector
in only 2/3 Sector flights because the realised body/velocity heading varied;
in run 3 it entered the sector. More importantly, Adaptive received 82, 78 and
88 future-risk verdicts, respectively, and all were FREE. Its 5/4/4 effective
Full openings were driven by existing replan/ordinary guard paths, not the
exact raw-window future-risk tier.

The deterministic replay witness remains valid as a component test: when a
trajectory-conflicting obstacle surface is actually placed in the raw scan,
the production C++ frontend returns fresh OCCUPIED while fixed Sector removes
the evidence. V4 shows that the same forced state did not arise naturally in
closed-loop flight. A future study must therefore use a separately named,
physically meaningful static blind-doorway fixture and first audit the actual
closed-loop committed trajectory; it must not further tune v4.

## Preserved evidence

- `results/angular_blind_turn_v4_route_gate_20260909.json`
- `results/angular_blind_turn_v4_liveness_gate_20260909.json`
- `results/frontend_replay_witness_abt4_observed_exit_gate_20260909.json`
- `results/angular_blind_turn_v4_full_n1_raw_20260909.csv`
- `results/angular_blind_turn_v4_full_n1_gate_20260909.json`
- `results/angular_blind_turn_v4_three_mode_n3_raw_20260909.csv`
- `results/angular_blind_turn_v4_three_mode_n3_gate_20260909.json`

The Full raw/gate hashes are
`34568bc441197016e9159c44fd6acfc17c20567c11d07d350ee4c2edb2135076`
and `904b8f834d11d4b8bc396012ba5b1b98c4e4a406e0c48330ea066656b8dfb0f0`.
The pilot raw/gate hashes are
`de981346851b28535bd874b01e55a3ca623956f79f52ed81e69600e87b9f72ba`
and `8db6e4697b77fc4dcd46655d3e4a6d281056eb87cd4028e3b74120b89eb78e0b`.
