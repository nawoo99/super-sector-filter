# Static blind-corner supplemental n=10 preregistration

Date frozen: 2026-09-08 (Asia/Seoul), before the first `occ_b` flight

## Role and separation from existing evidence

The existing Map1--10 reliability campaign and the completed v1/v2
static-occlusion pilots remain unchanged at sector-filter commit `7f158ee`.
This is an additional exploratory static stress test, not a replacement for
those results and not a confirmatory new-environment generalization study.

The deployed planner, v7 dynamics, 45-degree crop, Full policy, fixed Sector
ablation and Adaptive policy are frozen. No planner source or planner profile
was changed for this supplement. Only five new simulator maps, their
measurement registration and reproducible generation/analysis tooling were
added.

The five maps reuse one representative background from each original radius
stratum: source seeds 1, 3, 5, 7 and 9. Repeated runs within a map measure
stochastic execution reliability conditional on these five maps; they are not
treated as 50 independent environments.

## Final frozen map geometry

Every `occ_b_r1`--`occ_b_r5` map contains the same full-height solid-wall
blind corner. There is no sensor slit and no moving obstacle. The local patch
`x=[5.0,27.5], y=[5.0,27.5] m` is cleared before inserting the channel and
hazard. The channel retains the validated 1.80 m free half-width, 0.30 m wall
thickness and 3.20 m height used by v2.

The common vertical hazard cylinder is centred at `(18.8,24.0) m`, has radius
0.95 m and height 3.20 m. It is larger and closer to the first turn than the
v2 `(18.0,24.0)`, radius-0.75 m hazard. The wall and hazard cover the frozen
z=0.5--2.8 m flight envelope, so the fixed-height horizontal-slit defect found
in v2 is absent.

The first analytically visible point on the diagonal reference occurs at
`x=y=20.18 m`, 4.061625 m from the hazard centre. At that pose, the closest
hazard edge is 51.336 degrees from the 45-degree diagonal velocity direction:
the complete cylinder is outside a 45-degree half-angle crop with 6.336
degrees margin. Centre rays are blocked at `x=y=11,14,17,20 m`.

The map is difficult but not geometrically impossible. The deterministic
validator found a collision-free northern bypass with declared body
clearance +0.24 m from the wall and +0.21 m from the hazard. The reference
approach has +1.60 m wall and +2.942 m hazard body clearance.

An earlier no-flight geometry draft extended the inner wall separately by
tier. The fail-closed validator rejected it because its reference approach
intersected the wall. No simulator flight used that draft. The final geometry
above was regenerated, validated and frozen before execution.

Runtime PCDs are intentionally not committed because they total about 84 MiB;
`gen_static_blind_corner_supplement.py` and
`static_blind_corner_supplement_manifest.json` reproduce them and freeze their
hashes. The five small simulator configs are mirrored under
`super_patches/native_seedmap_campaign/perfect_drone_sim_config/`.

## Measurement and interpretation

The authoritative contact source remains the generated source PCD inflated by
the declared 0.20 m vehicle radius. The existing analytic cylinder monitor
also records hazard-specific contact and clearance. The C++ raw-input probe is
centred at `(18.8,24.0)` with radius 1.0 m and records first observation,
position, altitude, speed, body/velocity bearing, crop state and Adaptive-open
state before filtering.

The probe has no control/publication output but synchronously scans filtered
rows until first observation. Literal zero timing perturbation is not claimed.
Its cost is included in Sector/Adaptive and makes Full-relative computation
reductions conservative. The established resource-gated campaign remains the
primary computation evidence.

## Frozen execution sequence

First, one deployment smoke per map/mode (15 rows) is run in a separate file.
It is design/deployment evidence and is not pooled into the requested n=10
result. A Full or Adaptive incomplete/contact row stops before the 150-row run
for feasibility classification; a Sector outcome does not trigger map tuning.
No geometry or planner parameter may change after the first smoke row.

If the smoke has 10/10 safe Full/Adaptive rows, the reported campaign is five
maps x three modes x ten runs = 150 rows. Mode order rotates globally. Timeout
is 180 s and the normal resource preflight/runtime guard is enabled.

Smoke command:

```bash
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 scripts/native_campaign/native_campaign.py \
  --maps occ_b_r1 occ_b_r2 occ_b_r3 occ_b_r4 occ_b_r5 \
  --modes full sector adaptive --runs 1 --rotate-modes \
  --seedmap-full-super-config static_seedmaps_guard_viability_tight_v7.yaml \
  --seedmap-filtered-super-config static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml \
  --seedmap-adaptive-super-config static_seedmaps_guard_viability_tight_v7_frontend_risk_enforce.yaml \
  --seedmap-static-pcd --loop-timeout 180 \
  --filter-profile strict-burst --filter-backend cpp-frontend \
  --full-intra-process --filter-half-angle-deg 45 \
  --filtered-reliable-map-link \
  --adaptive-max-publish-hz 5 --adaptive-risk-max-eval-hz 5 \
  --adaptive-risk-body-clearance-m 0.20 \
  --adaptive-risk-body-horizon-s 0.15 \
  --adaptive-risk-body-max-odom-age-s 0.20 \
  --cgroup-cpu-accounting --optimizer-phase-memory-trace \
  --artifacts-dir results/static_blind_corner_smoke_three_mode_n1_artifacts_20260908 \
  --out results/static_blind_corner_smoke_three_mode_n1_raw_20260908.csv
```

The reported n=10 command is identical except:

```text
--runs 10
--artifacts-dir results/static_blind_corner_supplement_three_mode_n10_artifacts_20260908
--out results/static_blind_corner_supplement_three_mode_n10_raw_20260908.csv
```

## Frozen result audit and descriptive gates

The requested campaign is structurally valid only with 150 exact unique keys,
150 first-attempt run/resource/speed/performance/cgroup-valid rows, 100/100
valid filtered probes, 150/150 valid analytic hazard measurements, and no
retry/resource abort/infrastructure failure/OOM. Infrastructure-confounded
rows are preserved and classified rather than silently replaced.

The protected-mode goal is Full and Adaptive 100/100 complete and free of
authoritative contact. The physical-delivery diagnostic requires, within each
map, 20/20 filtered probes, pooled median first-observation distance in
`[2.5,5.5] m`, the hazard centre outside Sector's crop in at least 8/10 runs,
and at least one trajectory-guard opening in at least 8/10 Adaptive runs.

Safety separation is reported by two predeclared descriptive routes:

1. At least five matched run-level Sector-bad/Adaptive-safe discordances
   distributed across at least two maps, with no reverse discordance; or
2. Adaptive's within-run hazard-clearance difference has a positive median in
   at least 4/5 maps and the median of the five map medians is at least
   +0.10 m, with no reverse discordance.

These are screening thresholds, not population guarantees. Because ten runs
share each map, run-level discordances are clustered and will not be presented
as 50 independent environments. The analysis will report complete/contact,
mission time, global and hazard clearance, Adaptive effective/TG openings,
map compute, common end-to-end CPU and planner ingress per map and mode.

If protected modes fail, the failure is reported; neither planner nor map is
automatically changed and the campaign is not restarted as if the failure had
not occurred. If Sector does not degrade, the result remains a valid negative
supplemental result and the map is not made harder after inspection.

## Frozen identifiers

- SUPER source commit: `2ad3419c127a617c6d7df6925e81a14175a9c096`
- preserved sector-filter result commit: `7f158ee47b7d667d0c410f91e25f7d902e896e5d`
- runner SHA-256: `994faac898252510e75d3a1c26a8b125c21b6d11fe18b55d46d14459b0f4ed95`
- monitor SHA-256: `873638c582313a49ac8e9cba5522be7fcef4f84914508e01ce609c218201d6f2`
- generator SHA-256: `6e7a9e99ba90c4f74dab7881c5ce83d64f975c107aca2c6afe87bb676671a10e`
- validator SHA-256: `897d38ede5f158f31342675beb5cbf20626175b9d01c7132d034829cbda230a9`
- analyzer SHA-256: `c898d22a9ef153e1ba2ec7cec4765f0ea5129aa1aef9a9d83e882a6967b3bd43`
- manifest SHA-256: `3c01c1b917c06901da4ca13e43721643e10c81510947de9031e1b10065325674`
- mirrored C++ frontend SHA-256: `5feb942ce98030499214139555a54b0c822521d1f95fe015e856664181a1cdaa`
- installed frontend executable/component SHA-256:
  `95d676044708813b119ffc1d751e5b12c425e70fc091626f0d3e0b7eda861935`,
  `3b19ab30488b2b4de0de8f52d32bd064d5d7d3acddf7c273aa9039b3aaf97c40`
- Full/Sector/Adaptive config SHA-256:
  `6589b7c4065aa528facecc8f0f624c4f178718933afa537af861f4eb54cee540`,
  `eafae08a239cc4409b7df0b829f7951a0d26a0ea3ec5a97c3f03ad3a2b44eb24`,
  `82c8536181b1c402330d47a23c3b17311537f91105eca71337286d0d514277a7`
