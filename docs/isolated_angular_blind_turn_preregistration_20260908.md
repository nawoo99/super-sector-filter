# Isolated angular blind-turn calibration preregistration

Date frozen: 2026-09-08 (Asia/Seoul), before the first `abt2_cal` flight

## Question and separation

This is a new calibration family, `abt2_cal_t1..t5`.  It does not modify or
pool the preserved Map1--10, `occ_bw`, or failed `abt_cal` evidence.  The
planner and all Full/Sector/Adaptive policies remain frozen.  The only change
is the static experiment fixture required to isolate the intended angular
blind-zone mechanism.

The v1 `abt_cal` fixture had three identified confounds: the critical turn was
not the first turn, its five backgrounds and hazard sizes changed together,
and the hazard-centred raw probe overlapped the upper wall.  The sole Sector
failure occurred before the target turn, while Adaptive's exact frontend
future-trajectory brake appeared in only 2/5 rows.  Those 15 rows remain a
complete negative calibration and are never pooled with this version.

## Frozen v2 fixture

All five candidates start at `(24,0,1.5)` with yaw `pi/2` and run only:

```text
(24,0) --north--> (24,24) --west--> (0,24)
```

Thus the first waypoint switch is the only critical 90-degree turn.  Timeout
is 90 s and waypoint switch distance is 1.5 m.

Every candidate has the identical controlled background, guide posts, channel
and static hazard.  The only varied factor is aperture position:

| Map | aperture centre x (m) | first visible y (m) | minimum relative angle | worst-case lead at 7 m/s |
|---|---:|---:|---:|---:|
| `abt2_cal_t1` | 19.500 | 18.800 | 47.145 deg | 0.529 s |
| `abt2_cal_t2` | 19.575 | 19.005 | 48.061 deg | 0.499 s |
| `abt2_cal_t3` | 19.650 | 19.195 | 48.934 deg | 0.472 s |
| `abt2_cal_t4` | 19.725 | 19.375 | 49.778 deg | 0.446 s |
| `abt2_cal_t5` | 19.800 | 19.545 | 50.596 deg | 0.422 s |

Common geometry:

- static hazard centre `(16.2,24.4)` m, radius 1.20 m, height 3.20 m;
- lower occluding wall at `y=23.0`, from `x=14.0..23.2`, split by one
  full-height horizontal aperture;
- aperture width 0.38 m, smaller than the 0.40 m vehicle diameter;
- upper channel wall at `y=26.0`, from `x=14.0..23.2`;
- wall thickness 0.30 m, vehicle radius 0.20 m;
- symmetric guide posts at `x={22,26}`, `y={5,10,15}`, radius 0.15 m;
- validated body-height envelope `z=[0.5,2.8]` m.

The direct post-switch route intersects the hazard.  The common topology-
changing northern bypass has at least +0.45 m body-surface clearance.  A
fail-closed validator uses the actual 151-point horizontal cylinder lattice,
finite wall thickness and aperture end caps.  It passed before flight.

The raw-input probe is a 0.12 m patch on the first exposed hazard surface for
each aperture.  Each patch is disjoint from both walls.  It is not the old
hazard-centred radius probe and cannot count a wall point as a hazard reveal.

## Frozen execution

Run one first-attempt row for each map and mode: 5 maps x 3 modes = 15 rows.
Global mode order rotates.  Estimated wall-clock time is 15--25 minutes.

```bash
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 scripts/native_campaign/native_campaign.py \
  --maps abt2_cal_t1 abt2_cal_t2 abt2_cal_t3 abt2_cal_t4 abt2_cal_t5 \
  --modes full sector adaptive --runs 1 --rotate-modes \
  --seedmap-full-super-config static_seedmaps_guard_viability_tight_v7.yaml \
  --seedmap-filtered-super-config static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml \
  --seedmap-adaptive-super-config static_seedmaps_guard_viability_tight_v7_frontend_risk_enforce.yaml \
  --seedmap-static-pcd --loop-timeout 90 \
  --filter-profile strict-burst --filter-backend cpp-frontend \
  --full-intra-process --filter-half-angle-deg 45 \
  --filtered-reliable-map-link \
  --adaptive-max-publish-hz 5 --adaptive-risk-max-eval-hz 5 \
  --adaptive-risk-body-clearance-m 0.20 \
  --adaptive-risk-body-horizon-s 0.15 \
  --adaptive-risk-body-max-odom-age-s 0.20 \
  --resource-preflight-min-available-mib 7168 \
  --cgroup-cpu-accounting --optimizer-phase-memory-trace \
  --artifacts-dir results/isolated_angular_blind_turn_three_mode_n1_artifacts_20260908 \
  --out results/isolated_angular_blind_turn_three_mode_n1_raw_20260908.csv
```

The 7 GiB preflight threshold is the already documented pre-flight amendment
from v1: Pylance holds about 2.9 GiB.  Runtime 2 GiB, PSI, OOM, speed,
performance and cgroup gates are unchanged.

## Frozen mechanism gate

Proceed only if every condition holds:

1. Full is contact-free and completes in 5/5 rows.
2. Adaptive is contact-free and completes in 5/5 rows.
3. Adaptive records an exact, fresh, enforced C++ frontend future-trajectory
   risk brake in at least 4/5 rows.  Generic full-open transitions do not
   satisfy this condition.
4. Sector is degraded in at least 2/5 rows **at or after** reaching the target
   corner `(24,24)`.  A failure before that point does not count.
5. The isolated surface probe is observed outside the fixed 45-degree sector
   in all ten filtered rows.
6. All 15 rows are unique, first-attempt and quality-valid, with no retry,
   infrastructure failure, resource abort or OOM.

This is a calibration mechanism gate, not an inferential comparison.  No
McNemar or significance claim is made from n=1.

If the gate fails, preserve all rows, record the cause, and stop.  Do not run
an independent campaign and do not select a favourable candidate.  If it
passes, use the preselected median timing geometry `abt2_cal_t3`
(`aperture_x=19.65`) to generate five newly named evaluation maps, freeze
their hashes before their first flight, and only then run n=10 per map and
mode (150 rows).

## Frozen identifiers

- SUPER source base: `2ad3419c127a617c6d7df6925e81a14175a9c096`
- runner: `f2c8acbcd354ee5a78aa322c30e57b4eae1aa97e9fe656fd24110db0cbf06465`
- monitor: `873638c582313a49ac8e9cba5522be7fcef4f84914508e01ce609c218201d6f2`
- generator: `610f04a674dd1ee0658e1b855aa1ca376c014e1898ab31477d1293f8a2620693`
- validator: `efa0f144b53c3a67b13a6e84b9ed7302464fa29b8f348b96dd5dc57d8f396325`
- analyzer: `cb8f673ff318a301fd01fb28be6109ed6ad31e0bd45d312133a424a83f179968`
- manifest: `fab1577a1fbe7357b8f6f0d9af13865a181159bee2176016673e070d3daa8d19`
- waypoint: `52288ce7b7da5ab3fa27f5e20fecad291f3c3fbe4fb05f4d0b1baa5bb59da5f0`
- PCDs t1--t5:
  `552d59c27f3af191ad2236c5c3a1eff25a2eb998fe6b4edcd74d91de4a588559`,
  `51765726a7a34fb3f6f642faacc82f1976d2d8bda16800e467c6cc9fa71f3a0b`,
  `27d965f0384f68afd7c91f11dca26251c4a983a2e21fa3a9f40532ded447aec8`,
  `ed57c2dbc860022c6d102cd769f683485b6b43a4cd4cf9b74b6fc22d11e84f56`,
  `ca885cecc345008dd5660b7f92991531cf3c6d2bd6a1c7981e7071f2239b0709`.
