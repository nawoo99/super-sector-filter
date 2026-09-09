# Angular blind-turn v4 observed-exit gate preregistration

Date frozen: 2026-09-09 (Asia/Seoul), before the first `abt4_observed_exit` flight

## Question and separation

V3 showed Full/Adaptive completion and fixed-Sector timeout, but the Sector
failure was caused by an empty forward crop after passing the target. This v4
fixture removes that specific liveness confound before asking whether a true
blind-zone difference remains. It is a newly named development map and is not
pooled with v1--v3, Map1--10, `occ_bw`, or any evaluation result.

The planner and Full/Sector/Adaptive policies are unchanged. Relative to
`abt3_gate_open`, the only PCD change is a distant northern observation wall
from `(-10,29)` to `(24,29)`. Hazard, lower occluder, aperture, guide posts,
start, route, speed and timeout are unchanged.

## Frozen prerequisite gates

The actual PCD passed ROG-equivalent route validation. The first bypass anchor
is 6.539113 m away within the 7 m local horizon; all three A* segments exist
after 0.10 m / three-cell spherical inflation; minimum path-to-sampled-surface
distance is 0.550744 m. The direct route still intersects the 1.20 m hazard.

Actual MARSIM fixed-Sector replays at outgoing poses `(20,26.3,1.2)`,
`(12,26.3,1.2)` and `(4,26.3,1.2)`, all west-facing at 7 m/s, retained
5847.07, 2216.07 and 2206.40 points/frame respectively. The v3 zero-point
outgoing condition is therefore absent at all frozen stations.

The unchanged near-corner replay contract also passed: raw trajectory conflict
was present in every measured frame, fixed Sector leaked zero hazard/conflict
points, and Adaptive produced 25 consecutive fresh OCCUPIED verdicts. These
are component gates, not flight outcomes.

## Phase 1: Full-only feasibility smoke

Run exactly one first-attempt Full row:

```bash
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 scripts/native_campaign/native_campaign.py \
  --maps abt4_observed_exit --modes full --runs 1 \
  --seedmap-full-super-config static_seedmaps_guard_viability_tight_v7.yaml \
  --seedmap-filtered-super-config static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml \
  --seedmap-static-pcd --loop-timeout 90 \
  --filter-profile strict-burst --filter-backend cpp-frontend \
  --full-intra-process --filter-half-angle-deg 45 \
  --filtered-reliable-map-link \
  --resource-preflight-min-available-mib 7168 \
  --cgroup-cpu-accounting --optimizer-phase-memory-trace \
  --artifacts-dir results/angular_blind_turn_v4_full_n1_artifacts_20260909 \
  --out results/angular_blind_turn_v4_full_n1_raw_20260909.csv
```

Proceed only if the row is unique, first-attempt and fully quality-valid, with
no retry, infrastructure failure, resource abort or OOM, and Full completes
contact-free. Otherwise preserve the failure and do not run the three-mode
pilot.

## Phase 2: contingent three-mode n=3 pilot

Run only if Phase 1 returns `PROCEED_TO_THREE_MODE_N3`:

```bash
python3 scripts/native_campaign/native_campaign.py \
  --maps abt4_observed_exit --modes full sector adaptive --runs 3 --rotate-modes \
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
  --artifacts-dir results/angular_blind_turn_v4_three_mode_n3_artifacts_20260909 \
  --out results/angular_blind_turn_v4_three_mode_n3_raw_20260909.csv
```

The development gate requires all nine rows unique, first-attempt and
quality-valid; Full and Adaptive contact-free completion 3/3; Sector degraded
at or after the target in at least 2/3; zero Sector rows with
`guard_main_pre_map_stale`; exact fresh enforced Adaptive future-risk brakes in
at least 2/3; probe observation in all six filtered rows; and the probe outside
the fixed Sector in all three Sector rows.

Any failure produces `STOP_V4_THREE_MODE_GATE_FAILED`. Preserve all rows and do
not tune/retry or construct held-out maps. A pass permits only preregistration
of a separate held-out family. This n=1/n=3 sequence is not inferential; no
McNemar or population-level claim is allowed.

## Frozen identifiers

- SUPER source base: `2ad3419c127a617c6d7df6925e81a14175a9c096`
- PCD: `ceff36eb6916f4d1301d2dfd73529ee589f87840264382121c43a811c1a7e87f`
- simulator config: `0969033bc3f10535fc2a091f751b03dae7c23b66cbd455eaca3d6186695b4a27`
- manifest: `81b15cbed03e6a56edef6d4b18a6f9a2693fbeb328521900032a8719c34fda8c`
- generator: `9eeb441ff6d34816d032b741d10dc5a5013b98b0436d446107968c835deea734`
- route validator: `13857215cdf7b26af58bf7ad17aa0466a2cbbe27f1d48aee4e7db55e072cc066`
- liveness analyzer: `fd0ce02a4a0fcd93bffbdfe3f20ddcfc5342f9ed1c28de68f42d5e8601f0b6db`
- flight analyzer: `238b0a616592bcfd86eaa47fb0a8455158e894819519063eb0550c2e5a9b137b`
- runner: `d5d0a7b2a1359e8bc2bfe63b67ab5a63144012daabc651e4df8164f46b668be8`
- monitor: `873638c582313a49ac8e9cba5522be7fcef4f84914508e01ce609c218201d6f2`
- route gate: `f2356db893ec11a46a4f8a90134022ef0edbd3645734745c8e3b26f8c00937c2`
- liveness gate: `f2657b164bfd4d4df39a9cde3f2f3ea8228a5d62e6dcfeaca39d54d902873c02`
- replay gate: `c9370c50780e340e1ac6a0f9b183e1c28762e539e68a254cc4605c6e3897f597`
- waypoint: `52288ce7b7da5ab3fa27f5e20fecad291f3c3fbe4fb05f4d0b1baa5bb59da5f0`

The generator plus manifest are the versioned source for the large PCD. The
runtime PCD is reproducibly generated and is not committed.
