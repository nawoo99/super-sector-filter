# Angular blind-turn v3 staged gate result

Date: 2026-09-09 (Asia/Seoul)

## Decision

`abt3_gate_open` passed the route gate, actual-raycast/frontend replay gate and
Full-only flight gate. The contingent paired flight then produced the desired
completion separation—Full and Adaptive completed without contact while fixed
Sector timed out after the target turn—but failed the frozen mechanism gate.

The final decision is `STOP_PAIRED_MECHANISM_GATE_FAILED`. No retry,
replacement row or larger calibration was run. This n=1 result is development
evidence only; it is not a population estimate, McNemar test, or safety-
superiority claim.

## Map-labelled flight result

| Map | Mode | Complete | Contact | Time (s) | Waypoints | PCD clearance (m) | Hazard clearance (m) | Adaptive Full-open transitions | Exact future-risk brakes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `abt3_gate_open` | Full | 1 | 0 | 11.40 | 2/2 | 0.473 | 0.585 | — | 0 |
| `abt3_gate_open` | Sector | 0 | 0 | 90.01 | 1/2 | 0.416 | 0.414 | 0 | 0 |
| `abt3_gate_open` | Adaptive | 1 | 0 | 11.66 | 2/2 | 0.381 | 0.559 | 5 | 0 |

All three rows were unique, first-attempt and run/resource/speed/performance/
cgroup-valid. Retry, infrastructure failure, resource abort and OOM counts were
zero. Full therefore passed Phase 1. Phase 2 passed Sector degradation after
the target and Adaptive contact-free completion, but failed exact frontend
future-risk intervention and the two-row outside-sector surface-probe check.

## Computation and bandwidth diagnostics

| Map | Mode | Planner ingress (MiB/s) | Algorithm CPU (cores) | End-to-end CPU (cores) | Map compute (ms/frame) | Algorithm peak RSS (MiB) |
|---|---|---:|---:|---:|---:|---:|
| `abt3_gate_open` | Full | 3.407 | 1.037 | 1.091 | 6.128 | 3228.6 |
| `abt3_gate_open` | Sector | 0.134 | 0.148 | 0.400 | 4.005 | 3119.7 |
| `abt3_gate_open` | Adaptive | 0.989 | 0.856 | 1.107 | 5.161 | 3123.9 |

Full and Adaptive have comparable completion times. Against Full, Adaptive
reduced planner ingress 70.97%, algorithm CPU 17.47%, map compute time 15.78%
and algorithm peak RSS 3.24%; end-to-end CPU was 1.48% higher. Sector's much
lower averages are not a fair completed-mission efficiency comparison because
it spent about 80 s stationary after entering fail-closed stop.

## Why Sector failed

Sector did not collide with the hazard. It passed the intended corner and
reached approximately `(11.191,26.322,1.004)`, 11.43 m from the final goal.
At that state the forward crop repeatedly produced empty/non-dense clouds:
the remaining map features were behind or outside the narrow forward sector.
SUPER therefore stopped accepting map callbacks at version 85. Map age crossed
the 0.500 s limit at 0.507 s and `TrajectoryGuardFailClosed` entered
`EMER_STOP`. The map never refreshed, and 782 subsequent brake retries were
rejected while the row remained safely stationary until timeout.

This is a fixed-sector observability/liveness failure, not a contact caused by
the target cylinder. It does demonstrate that the upper-wall removal fixed the
old Full feasibility confound: Full completed in 11.40 s rather than reproducing
the v2 90 s local-dead-end timeout.

## Why Adaptive completed without an exact risk brake

The raw risk worker was healthy: it received 48 unique trajectory generations,
published 78 future verdicts at 4.968 Hz, and used 1.108 ms mean / 7.738 ms max
per evaluation. Every verdict was FREE, so planner-side future-risk received,
occupied, enforced and brake counts were all zero.

Adaptive instead observed 115 replan statuses, including 67 failures and a
maximum failure streak of 11. Its bounded replan guard opened the full field
five times (19.231% duty). The surface probe was first seen during one of these
open periods at `(24.207,13.748)`, 12.641 m away. At that instant its bearing
was 98.411 degrees from body yaw but only 9.466 degrees from velocity yaw, so
the frozen counterfactual marked the probe inside the velocity-aligned sector.
Early Full-open perception let subsequent planned trajectories use the northern
bypass; by the time the vehicle reached the corner, no committed 1 s trajectory
intersected raw hazard points. Thus replay OCCUPIED and closed-loop FREE are
consistent: the deterministic replay forced a colliding trajectory, whereas
the closed loop had already replanned around the hazard.

The observed Adaptive-over-Sector completion improvement is therefore
attributable to the existing bounded replan-triggered Full opening, not to the
new exact future-trajectory risk tier. It is a valid liveness mechanism result,
but it cannot satisfy the preregistered trajectory-risk or collision-safety
claim.

## Preserved evidence

- `results/angular_blind_turn_v3_route_gate_20260909.json`
- `results/frontend_replay_witness_abt3_gate_open_gate_20260909.json`
- `results/angular_blind_turn_v3_full_n1_raw_20260909.csv`
- `results/angular_blind_turn_v3_full_n1_gate_20260909.json`
- `results/angular_blind_turn_v3_sector_adaptive_n1_raw_20260909.csv`
- `results/angular_blind_turn_v3_sector_adaptive_n1_gate_20260909.json`

The raw result hashes are respectively
`9619875e6427e7481738685bb663fcfaf0ff09502b50787d5d06056e05d56342`
and `36723259710b3d5f3a2b471696037f4da88cfa1d15bd126a3fd9ac8d92c687ef`;
the gate hashes are
`7323ac3e6d572182fb8bba43719d3601f735cbca55ecbb464ea8441ddc84da35`
and `b5171a026589d206ae8f28b88ad37942bbf9d6c11032635aee50d330ec4293af`.
