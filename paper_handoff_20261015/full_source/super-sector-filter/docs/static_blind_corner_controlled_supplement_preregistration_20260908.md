# Controlled-route static blind-corner supplemental n=10 preregistration

> **Frozen v3.1 feasibility outcome (2026-09-08): stopped as specified.** Six
> rows were committed before the stop. Five completed and all six had zero
> authoritative contact, but `occ_bc_r2` Full reached only 1/5 waypoints at the
> 180 s timeout. The row was resource-, speed- and infrastructure-valid. It
> recorded 209 reroute arms and 627 searches, dominated by repeated
> `trajectory_optimization_overtime`. The nominal northern bypass supplied
> only +0.24 m wall and +0.21 m hazard body clearance, almost identical to the
> 0.20 m planner margin. This made the protected Full condition a boundary
> case rather than isolating Sector visibility. No 150-row campaign began.
> The six-row raw smoke is
> `static_blind_corner_controlled_smoke_three_mode_n1_raw_20260908.csv`.
> The separately preregistered `occ_bw` successor widens this bypass without
> changing the hazard, sensor policies or planner.

Date frozen: 2026-09-08 (Asia/Seoul), before the first `occ_bc` flight

## Why this is a separate successor

The original `occ_b` feasibility smoke stopped exactly as preregistered when
Full timed out on `occ_b_r4`. The failure and its successful non-pooled replay
remain preserved in the v3 preregistration and raw CSVs. Logs locate the stall
on the inherited seed7 south leg, not at the added north-east blind corner.
Consequently `occ_b` mixed two causes: the intended side-reveal intervention
and unrelated random background bottlenecks.

This v3.1 successor isolates the intervention. It removes every *background*
cylinder whose surface lies within 2.0 m of the fixed mission polyline
`(0,0)->(24,24)->(-24,24)->(-24,-24)->(24,-24)->(0,0)`. The solid walls and
hazard added at the north-east corner are inserted after this removal and are
not cleared. The five radius-stratified backgrounds still surround the route
and preserve different point counts and sensing/compute loads.

This is a map-design correction, not planner tuning. SUPER source commit,
Full/Sector/Adaptive profiles, v=7 dynamics, 45-degree crop, guard settings
and C++ frontend are unchanged. Existing Map1--10 and v1/v2/v3 evidence is not
replaced or pooled with this supplement.

## Frozen maps and analytic checks

The reported maps are `occ_bc_r1`--`occ_bc_r5`, derived from source seeds
1, 3, 5, 7 and 9 (background cylinder radii 0.150, 0.275, 0.400, 0.525 and
0.650 m). They contain 317,881; 478,987; 618,247; 755,527; and 878,947 PCD
points, respectively. The common local patch, full-height L channel and
vertical hazard are identical to frozen v3:

- local replacement patch: `x,y=[5.0,27.5] m`;
- channel free half-width 1.80 m, wall thickness 0.30 m, height 3.20 m;
- hazard centre `(18.8,24.0) m`, radius 0.95 m, height 3.20 m;
- validated flight envelope `z=[0.5,2.8] m`, vehicle radius 0.20 m;
- diagonal reveal at `x=y=20.18 m`, centre distance 4.061625 m;
- nearest hazard edge 51.336 degrees from the velocity direction, hence the
  entire hazard is outside the fixed 45-degree crop with 6.336 degrees margin;
- validated reference approach clearances: wall +1.60 m, hazard +2.942 m;
- validated northern bypass clearances: wall +0.24 m, hazard +0.21 m.

The generator manifest records background removals and asset hashes. The
fail-closed validator reconstructs route-corridor removal counts from each
source CSV, checks the analytic blind geometry, 3-D coverage, PCD/config hashes
and bypass feasibility. It passed before flight. Runtime PCDs are generated in
the SUPER workspace and are not committed; the generator and manifest are the
tracked source of truth.

## Frozen execution and stopping rule

Run a new, separate one-per-cell smoke first (15 rows). It is deployment
evidence only and is not pooled with n=10. A Full or Adaptive incomplete or
contact row stops before the reported campaign for classification. Sector
outcomes never trigger map tuning. No planner, profile or `occ_bc` geometry may
change after the first smoke row.

If all ten protected smoke rows are complete and contact-free, run from
scratch five maps x three modes x ten repetitions = 150 reported rows. Global
mode order rotates, timeout is 180 s, and normal resource guards remain on.
Infrastructure-confounded attempts are preserved and classified, never
silently replaced. A failure in the 150 rows is reported without modifying or
restarting the campaign.

```bash
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 scripts/native_campaign/native_campaign.py \
  --maps occ_bc_r1 occ_bc_r2 occ_bc_r3 occ_bc_r4 occ_bc_r5 \
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
  --artifacts-dir results/static_blind_corner_controlled_smoke_three_mode_n1_artifacts_20260908 \
  --out results/static_blind_corner_controlled_smoke_three_mode_n1_raw_20260908.csv
```

The reported command is identical except for `--runs 10` and paths:

```text
--artifacts-dir results/static_blind_corner_controlled_three_mode_n10_artifacts_20260908
--out results/static_blind_corner_controlled_three_mode_n10_raw_20260908.csv
```

## Frozen validity and descriptive gates

The requested result requires 150 exact unique keys and 150 first-attempt
run/resource/speed/performance/cgroup-valid rows, 100 valid filtered raw probes,
150 valid analytic hazard measurements, and no retry, resource abort,
infrastructure failure or OOM. Full and Adaptive are protected: all 100 rows
must complete without authoritative contact.

Physical delivery is evaluated per map: 20/20 filtered probes; pooled median
first-observation distance in `[2.5,5.5] m`; Sector hazard centre outside the
crop in at least 8/10; Adaptive trajectory-guard active in at least 8/10.
Safety separation is descriptive and passes either of two frozen routes:

1. at least five matched Sector-bad/Adaptive-safe rows across at least two
   maps, with zero reverse rows; or
2. positive Adaptive-minus-Sector hazard-clearance median in at least 4/5
   maps and median of map medians at least +0.10 m, with zero reverse rows.

A safe but non-separating outcome remains a valid negative result. Ten repeats
within a map estimate conditional execution reliability and are not described
as 50 independent environments. Final reporting includes per-map completion,
contact, time, global/hazard clearance, Adaptive openings, map compute, common
end-to-end CPU and planner ingress bandwidth.

## Frozen identifiers

- SUPER source commit: `2ad3419c127a617c6d7df6925e81a14175a9c096`
- preserved result base: `276b33eafba1203d187b18f8c2464957762bab93`
- runner SHA-256: `6dab1e8bc850c9cb2c41cad988872732c366f28304a40416d970369581b51c23`
- monitor SHA-256: `873638c582313a49ac8e9cba5522be7fcef4f84914508e01ce609c218201d6f2`
- generator SHA-256: `f5c7c66920d5fd2b5d398be19bb1d6069795e49c35b95e6e93785076216b6137`
- validator SHA-256: `1f8ca30742d85f923a58238c69dcc9f4f0d3df0654e16cad26b83003d7b4bc73`
- analyzer SHA-256: `3c1a40295ac2cf7c3794293a37257d0a27b48920fc51b298c1f6b0bcb07bd6d0`
- manifest SHA-256: `63d10a64718c2c0a77d0eeb76c51a0b103063ef4d9c1134880068b7c41d9c591`
- mirrored/installed C++ frontend SHA-256:
  `5feb942ce98030499214139555a54b0c822521d1f95fe015e856664181a1cdaa`,
  `95d676044708813b119ffc1d751e5b12c425e70fc091626f0d3e0b7eda861935`,
  `3b19ab30488b2b4de0de8f52d32bd064d5d7d3acddf7c273aa9039b3aaf97c40`;
- Full/Sector/Adaptive config SHA-256:
  `6589b7c4065aa528facecc8f0f624c4f178718933afa537af861f4eb54cee540`,
  `eafae08a239cc4409b7df0b829f7951a0d26a0ea3ec5a97c3f03ad3a2b44eb24`,
  `82c8536181b1c402330d47a23c3b17311537f91105eca71337286d0d514277a7`;
- PCD SHA-256 r1--r5:
  `bad6427deac4e650059be347ecaafbd53ba9a0ba409a2c2fccb6979f1daed516`,
  `5b40879c4125830b5d018e98d88fa844f8dcf1d7fa53e220f77582a5c8a9bfc8`,
  `03ed1fc6a8ac0b7f86c71e59b9a8282d0bb1b3acc157abd470e78c64e42308e2`,
  `d5d9cd1997f869499af96d3bd464e03e3f3c3cdab57be7cd386e6ad23b9e7af3`,
  `6d57371071fa262f381bcbcf88cd8ec8823160c9bd4492fac16bb2c89980d018`.
