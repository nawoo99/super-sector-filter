# Angular blind-turn v3 staged gate preregistration

Date frozen: 2026-09-09 (Asia/Seoul), before the first `abt3_gate_open` flight

## Question and separation

This is one newly named development map. It is not pooled with Map1--10,
`occ_bw`, or the failed `abt_cal`/`abt2_cal` campaigns. The planner and all
Full/Sector/Adaptive policies remain frozen. The only geometry change from
`abt2_cal_t3` is removal of the upper channel wall, which provides a forward
northern bypass instead of the previously observed local dead end.

The experiment is staged. First run exactly one Full row. Sector and Adaptive
must not be flown unless that Full row passes its feasibility gate. This is an
n=1 development decision, not inferential evidence; no McNemar test or
population-level safety claim is permitted.

## Frozen geometry and prerequisite gates

- start `(24,0,1.5)`, yaw north;
- route `(24,24) -> (0,24)` using `turn90_isolated.txt`;
- static hazard centre `(16.2,24.4)` m, radius 1.20 m, height 3.20 m;
- lower occluding wall and 0.38 m aperture copied from `abt2_cal_t3`;
- upper channel wall absent;
- vehicle/body radius 0.20 m; ROG validation uses the actual 0.10 m lattice
  and its three-cell spherical inflation;
- timeout 90 s and waypoint switch distance 1.5 m.

Before flight, the actual generated PCD passed the route gate: the first
northern bypass anchor is 6.539113 m away, within the 7 m planning horizon;
the three A* segments exist after ROG-equivalent inflation; the minimum path
distance to sampled PCD surface is 0.550744 m. The direct route intersects the
hazard (`0.400000 < 1.200000` m).

The deterministic actual-MARSIM replay also passed. In both modes raw hazard
and evaluated-path conflict were present in 50/50 frames. Fixed Sector emitted
zero hazard/conflict points. Adaptive emitted 25 consecutive fresh OCCUPIED
future verdicts; its last minimum distance was 0.194958 m and source age was
0.001151 s. These are prerequisite component checks, not flight outcomes.

## Phase 1: frozen Full-only smoke

```bash
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 scripts/native_campaign/native_campaign.py \
  --maps abt3_gate_open --modes full --runs 1 \
  --seedmap-full-super-config static_seedmaps_guard_viability_tight_v7.yaml \
  --seedmap-filtered-super-config static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml \
  --seedmap-static-pcd --loop-timeout 90 \
  --filter-profile strict-burst --filter-backend cpp-frontend \
  --full-intra-process --filter-half-angle-deg 45 \
  --filtered-reliable-map-link \
  --resource-preflight-min-available-mib 7168 \
  --cgroup-cpu-accounting --optimizer-phase-memory-trace \
  --artifacts-dir results/angular_blind_turn_v3_full_n1_artifacts_20260909 \
  --out results/angular_blind_turn_v3_full_n1_raw_20260909.csv
```

Proceed only if the sole row is unique and first-attempt, all run/resource/
speed/performance/cgroup gates are valid, no retry/infrastructure failure/
resource abort/OOM occurs, and Full completes with zero live/static/hazard
contact. Otherwise preserve the row and stop without flying filtered modes.

## Phase 2: contingent paired mechanism smoke

Run only after Phase 1 returns `PROCEED_TO_PAIRED_MECHANISM_SMOKE`:

```bash
python3 scripts/native_campaign/native_campaign.py \
  --maps abt3_gate_open --modes sector adaptive --runs 1 --rotate-modes \
  --seedmap-full-super-config static_seedmaps_guard_viability_tight_v7.yaml \
  --seedmap-filtered-super-config static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml \
  --seedmap-adaptive-super-config static_seedmaps_guard_viability_tight_v7_frontend_risk_enforce.yaml \
  --seedmap-static-pcd --loop-timeout 90 \
  --filter-profile strict-burst --filter-backend cpp-frontend \
  --filter-half-angle-deg 45 --filtered-reliable-map-link \
  --adaptive-max-publish-hz 5 --adaptive-risk-max-eval-hz 5 \
  --adaptive-risk-body-clearance-m 0.20 \
  --adaptive-risk-body-horizon-s 0.15 \
  --adaptive-risk-body-max-odom-age-s 0.20 \
  --resource-preflight-min-available-mib 7168 \
  --cgroup-cpu-accounting --optimizer-phase-memory-trace \
  --artifacts-dir results/angular_blind_turn_v3_sector_adaptive_n1_artifacts_20260909 \
  --out results/angular_blind_turn_v3_sector_adaptive_n1_raw_20260909.csv
```

The paired mechanism gate requires: both rows unique, first-attempt and
quality-valid; Sector degraded at or after reaching the target corner;
Adaptive contact-free completion; at least one exact fresh enforced frontend
future-risk brake in Adaptive; and the isolated surface probe observed outside
the fixed sector in both rows. Failure means stop and diagnose. Success permits
designing a separately named multi-map calibration; it does not itself permit
a safety-superiority claim.

## Frozen identifiers

- SUPER source base: `2ad3419c127a617c6d7df6925e81a14175a9c096`
- PCD: `f53156b6661fdf8df868a5ab969897a6af9b76998db507ad1846e3bd9176e3f5`
- simulator config: `d042ee2f4aa3d91b2db6d10de57c72ffdf979eb0b191bef9608f3cc297168c38`
- manifest: `e7b579dbee0c1706e7da78e2618f07cd1a917fb563e8f47b1b1a03403ee4a4fe`
- generator: `a498f3b8fafd82a63edb4c34a3f6fd3ce4b59f0310686907f71f2996b693af47`
- route validator: `c7b5e586e583735cc2f760a3e590cb014bd76ca9df03e8ca0d9634d30468d1f8`
- route result: `7236768275f20d4841de5454744bd61232d0c10435ca29748251efbd74c261ca`
- runner: `c9e80936dc262288e664ef5d1f3c33a6ffc81cc5606c379606eb1c65af2557e4`
- monitor: `873638c582313a49ac8e9cba5522be7fcef4f84914508e01ce609c218201d6f2`
- flight analyzer: `6cd0ccbfab721cf665246a4054e4d598770363e78f58d160b1d10dcc1e0971b4`
- replay analyzer: `8028da969f0cb05c58f62d0393bab6e186ba1ad57c5cfdf54a6839829254b92d`
- replay gate result: `6d876470f69216fe79f1992403000432fba391e1600bb97640e6b576023f3811`
- replay Sector row: `b64af16d6d0e5c1c535e340b8257354275cead98d55f72774a0624ece4da4ced`
- replay Adaptive row: `bbfd4b1d7e2031a8fc651aaa902d845243387b299c1b1fdab89f68c56f4eed64`
- waypoint: `52288ce7b7da5ab3fa27f5e20fecad291f3c3fbe4fb05f4d0b1baa5bb59da5f0`

The generator plus manifest are the versioned source for the large PCD; the
runtime PCD itself is reproducibly generated and is not committed.
