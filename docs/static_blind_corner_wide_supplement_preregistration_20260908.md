# Wide-bypass static blind-corner supplemental n=10 preregistration

> **Frozen smoke outcome (2026-09-08): proceed.** All 15 rows completed on
> their first attempt with zero authoritative contact; all 15 were resource-,
> speed-, performance-, cgroup- and infrastructure-valid. Mission time ranged
> from 51.89 to 55.95 s. Full and Adaptive therefore passed the preregistered
> 10/10 protected smoke condition. Raw-probe first-observation distances were
> mixed (roughly 3.91--10.32 m), and Adaptive trajectory-guard opening occurred
> in 3/5 smoke rows. Thus the later physical-delivery gate may fail; this is
> not a stopping condition and no asset, planner or profile is changed before
> the 150-row run. The smoke remains separate at
> `results/static_blind_corner_wide_smoke_three_mode_n1_raw_20260908.csv`.

Date frozen: 2026-09-08 (Asia/Seoul), before the first `occ_bw` flight

## Scope and design history

This remains an additional exploratory check. It does not replace or pool
with the existing Map1--10 reliability evidence. The deployed planner, v=7
dynamics, Full policy, fixed 45-degree Sector crop, Adaptive policy and C++
frontend are unchanged.

Two earlier map-feasibility attempts are retained as negative design evidence:

- `occ_b_r4` Full timed out on an unrelated inherited seed7 south-leg
  bottleneck; its identical replay completed, identifying stochastic
  background-route confounding.
- after removing those background-route bottlenecks, `occ_bc_r2` Full timed
  out with 209 reroute arms and 627 searches. Its northern bypass had only
  +0.24 m wall/+0.21 m hazard body clearance, nearly equal to the planner's
  0.20 m margin. This was a map feasibility defect, not a Sector-specific
  stressor.

Both stopped smokes and raw CSVs are committed. Neither launched a 150-row
campaign. `occ_bw` is a separately named and hashed successor; no result from
the earlier attempts will be pooled into its requested n=10 result.

## Frozen five-map family

The five maps use source seeds 1, 3, 5, 7 and 9, one from each original
background-radius stratum (0.150, 0.275, 0.400, 0.525, 0.650 m). Background
cylinders whose surfaces lie within 2.0 m of the common loop24 mission
polyline are removed to isolate the north-east intervention. The surrounding
background and its point-load strata remain.

Common solid geometry:

- full-height L channel with 2.50 m free half-width, 0.30 m wall thickness
  and 3.20 m height;
- vertical hazard cylinder at `(18.4,24.0) m`, radius 0.95 m, height 3.20 m;
- vehicle radius 0.20 m and validated `z=[0.5,2.8] m` flight envelope;
- first diagonal reveal at `x=y=20.06 m`, 4.275418 m from the hazard centre;
- nearest hazard edge 55.008 degrees from velocity direction, so the entire
  hazard is outside the 45-degree crop with 10.008 degrees margin;
- centre rays blocked at diagonal stations 11, 14, 17 and 20 m;
- reference approach body clearances: wall +1.115 m, hazard +3.153 m;
- northern bypass body clearances: wall +0.575 m, hazard +0.575 m.

The PCD sizes are 319,001; 480,107; 619,367; 756,647; and 880,067 points.
The fail-closed validator reconstructs background corridor-removal counts,
checks the solid 3-D geometry, side-reveal angle, reference paths, hashes and
runtime configs. It passed before flight. Generated PCDs remain runtime-only;
the tracked generator and manifest are the reproducible source.

## Frozen execution

First run a separate one-per-cell smoke (15 rows). A Full or Adaptive
incomplete/contact row stops before the requested campaign for classification.
Sector outcomes do not cause map changes. The smoke is not pooled into n=10.
After the first smoke row, neither geometry nor planner/profile parameters may
change.

If all ten protected smoke rows complete contact-free, run five maps x three
modes x ten repetitions = 150 reported rows from scratch. Global mode order
rotates, timeout is 180 s and normal resource guards remain enabled. Any
protected failure in the 150 rows is retained and reported without modifying
or restarting the campaign.

```bash
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 scripts/native_campaign/native_campaign.py \
  --maps occ_bw_r1 occ_bw_r2 occ_bw_r3 occ_bw_r4 occ_bw_r5 \
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
  --artifacts-dir results/static_blind_corner_wide_smoke_three_mode_n1_artifacts_20260908 \
  --out results/static_blind_corner_wide_smoke_three_mode_n1_raw_20260908.csv
```

The reported command is identical except for `--runs 10` and:

```text
--artifacts-dir results/static_blind_corner_wide_three_mode_n10_artifacts_20260908
--out results/static_blind_corner_wide_three_mode_n10_raw_20260908.csv
```

## Frozen audit and interpretation

Structural validity requires 150 exact unique keys and 150 first-attempt
run/resource/speed/performance/cgroup-valid rows, 100 valid filtered probes,
150 valid hazard measurements, and no retry/resource abort/infrastructure
failure/OOM. Full and Adaptive are protected: 100/100 must complete without
authoritative contact.

Physical delivery is checked per map: 20/20 filtered probes; pooled median
first-observation distance in `[2.5,5.5] m`; Sector hazard centre outside crop
in at least 8/10; Adaptive trajectory-guard active in at least 8/10. Safety
separation passes either predeclared descriptive route:

1. at least five matched Sector-bad/Adaptive-safe rows across at least two
   maps, with no reverse row; or
2. positive Adaptive-minus-Sector hazard-clearance median in at least 4/5
   maps and median of map medians at least +0.10 m, with no reverse row.

A safe/non-separating outcome is retained as a valid negative result. Ten
repetitions per map estimate conditional execution reliability and are not
treated as 50 independent environments. Reporting includes completion,
contact, mission time, global/hazard clearance, Adaptive openings, map
compute, common end-to-end CPU and planner-ingress bandwidth by map and mode.

## Frozen identifiers

- SUPER source commit: `2ad3419c127a617c6d7df6925e81a14175a9c096`
- preserved result base: `ba96e622d08067049fcea04ab284fa15aaa54588`
- runner SHA-256: `8bedd6ea5c0949ca6d032290590f740bb2151da91b4b1983f214677d46abbc08`
- monitor SHA-256: `873638c582313a49ac8e9cba5522be7fcef4f84914508e01ce609c218201d6f2`
- generator SHA-256: `c0c3d5b0a4b81803930f729a728d7371fdf99fb17c14f75512c2c1042f549fc1`
- validator SHA-256: `0fbeb60f510fade75a2985217e1ab8945972f3fa51568f3f95f2f7a965b7c8ce`
- analyzer SHA-256: `b314bae0af33e5ce91e41a85c197c82d7c127b62e4436af297174699ba46b69d`
- manifest SHA-256: `c222d482c19e779b2c1506b688b6f72b1e5c2a231b346cc40445153bc78f0b0e`
- Full/Sector/Adaptive config SHA-256:
  `6589b7c4065aa528facecc8f0f624c4f178718933afa537af861f4eb54cee540`,
  `eafae08a239cc4409b7df0b829f7951a0d26a0ea3ec5a97c3f03ad3a2b44eb24`,
  `82c8536181b1c402330d47a23c3b17311537f91105eca71337286d0d514277a7`;
- PCD SHA-256 r1--r5:
  `ba218b8614c8509cfdbb3b3d363cbddae019afb4f810f35a56193daab58af925`,
  `77001a53617217df01ee580782670eb7564685cdde96bc79617c9819cac58701`,
  `8c06591306aeaeb64868be2d05d5ec434b8884d4fd24c67798f222fc25fb4cc2`,
  `eff53f16e543380932dbf5e8c7b1b13b76a1027c5d469300ea13d5763466310c`,
  `2a52df0ea155e50ef6df198e22d63b09f0a3cb901fb0e1016a33658f325adb62`.
