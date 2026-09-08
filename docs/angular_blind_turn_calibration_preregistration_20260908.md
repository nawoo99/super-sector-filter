# 90-degree angular blind-turn calibration preregistration

Date frozen: 2026-09-08 (Asia/Seoul), before the first `abt_cal` flight

> **Pre-flight infrastructure amendment (2026-09-08):** the first process
> remained at resource preflight and was interrupted before any launch or data
> row.  Its CSV contained only the header.  VS Code Pylance held about 2.9 GiB,
> leaving MemAvailable stable near 7.6 GiB, below the default 8 GiB threshold.
> To avoid killing a user process, the frozen command adds
> `--resource-preflight-min-available-mib 7168`.  The runtime 2 GiB minimum,
> PSI hold, resource abort, OOM and all row-validity gates are unchanged.

## Purpose and separation from prior evidence

The preserved Map1--10 reliability campaign and the completed `occ_bw_r1..r5`
supplement are not changed or pooled with this experiment.  The deployed
planner, v=7 dynamics, Full policy, fixed 45-degree Sector crop, Adaptive
policy, C++ frontend, resource guard and measurement pipeline are frozen.

The prior `occ_bw` result was a valid negative result: all three modes were
50/50 safe, and Adaptive trajectory-risk braking was not consistently
delivered.  Its first critical turn was 135 degrees, and the fixed-sector
planner still had enough time and open topology to replan after seeing the
hazard.  This calibration asks a narrower mechanism question: can a static
90-degree turn deliver an obstacle to raw 360-degree sensing outside the
45-degree crop, make the newly committed outgoing trajectory unsafe, and
force a topology-changing exit from a bounded channel?

## Frozen calibration assets

The five calibration candidates are `abt_cal_s1..s5`.  They use source
backgrounds 1, 3, 5, 7 and 9, with background cylinders removed only when
their surface lies within 2.0 m of the common controlled route or intersects
the existing local north-east patch.  This retains five point-load/radius
strata while isolating the intervention.

The route is:

```text
(0,0) -> (24,0) -> (24,24) -> (-24,24) ->
(-24,-24) -> (24,-24) -> (0,0)
```

The critical transition at `(24,24)` is exactly 90 degrees, northbound to
westbound.  Every waypoint uses a 1.5 m switch distance.

Common intervention geometry:

- lower solid wall from `(14.0,22.0)` to `(23.2,22.0)` m;
- upper solid wall from `(14.0,25.2)` to `(23.2,25.2)` m;
- both walls are 0.30 m thick and 3.20 m high;
- static hazard centre `(18.5,24.0)` m and height 3.20 m;
- hazard radii 1.10, 1.20, 1.30, 1.40 and 1.50 m for severities 1--5;
- vehicle radius 0.20 m and validated flight envelope `z=[0.5,2.8]` m.

The lower wall is both a real channel boundary and the occluder.  The
fail-closed geometric validator finds the first visible hazard surface at
northbound `y=21.52..21.61` m.  At first visibility its nearest surface ray
is still `51.449..55.943` degrees from the northbound filter centre, outside
the fixed 45-degree crop.  The direct westbound route intersects the hazard.
A common northern topology-changing bypass has at least +0.450 m physical
body clearance.  Validation passed before flight.

## Frozen calibration execution and gate

Run one first-attempt row per map and mode: five maps x Full/Sector/Adaptive =
15 rows.  Global mode order rotates.  Timeout is 210 s.  The smoke is
calibration-only and can never be pooled into an independent evaluation.

```bash
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 scripts/native_campaign/native_campaign.py \
  --maps abt_cal_s1 abt_cal_s2 abt_cal_s3 abt_cal_s4 abt_cal_s5 \
  --modes full sector adaptive --runs 1 --rotate-modes \
  --seedmap-full-super-config static_seedmaps_guard_viability_tight_v7.yaml \
  --seedmap-filtered-super-config static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml \
  --seedmap-adaptive-super-config static_seedmaps_guard_viability_tight_v7_frontend_risk_enforce.yaml \
  --seedmap-static-pcd --loop-timeout 210 \
  --filter-profile strict-burst --filter-backend cpp-frontend \
  --full-intra-process --filter-half-angle-deg 45 \
  --filtered-reliable-map-link \
  --adaptive-max-publish-hz 5 --adaptive-risk-max-eval-hz 5 \
  --adaptive-risk-body-clearance-m 0.20 \
  --adaptive-risk-body-horizon-s 0.15 \
  --adaptive-risk-body-max-odom-age-s 0.20 \
  --resource-preflight-min-available-mib 7168 \
  --cgroup-cpu-accounting --optimizer-phase-memory-trace \
  --artifacts-dir results/angular_blind_turn_calibration_three_mode_n1_artifacts_20260908 \
  --out results/angular_blind_turn_calibration_three_mode_n1_raw_20260908.csv
```

Proceed to independent evaluation only if all conditions hold:

1. Full completes contact-free in 5/5 rows.
2. Adaptive completes contact-free in 5/5 rows.
3. Adaptive has `frontend_risk_brake_events > 0` in at least 4/5 rows; this is
   the specific raw-window future-trajectory intervention, not a generic
   full-open transition.
4. Sector is degraded in at least 2/5 rows, where degraded means incomplete
   mission or authoritative global/static-hazard contact.
5. All 15 rows are first-attempt, run/resource/speed/performance/cgroup-valid,
   without retry, infrastructure failure, resource abort or OOM.

If the gate fails, retain and report the complete calibration result and stop.
Do not launch 150 evaluation rows and do not select only favourable severity
rows.  A later redesign must receive a new map-family/version name and a new
preregistration.

If the gate passes, create five newly seeded, independently named evaluation
maps with the frozen selected geometry, preregister their hashes before the
first evaluation flight, then run Full/Sector/Adaptive n=10 per map (150 rows).

## Frozen identifiers

- SUPER source base commit: `2ad3419c127a617c6d7df6925e81a14175a9c096`
- preserved mirror result commit: `864a19519ba15a94d1ac8845a04a7eca1474c34f`
- runner SHA-256: `1b6c48a4cd963ed2ea9ba3d8fec4949a288c34a43aff6096a1c72bc407687b05`
- monitor SHA-256: `873638c582313a49ac8e9cba5522be7fcef4f84914508e01ce609c218201d6f2`
- generator SHA-256: `bd1a9cf1d2113a054cf9da70164bc0ac14e23324f64f0445471028bd5bf9897f`
- validator SHA-256: `6080e833d38d7c57fa221dffc05f74ee1424a59c721cc4b5c814af0bd0c94b86`
- manifest SHA-256: `9b44f1280eed7458d874c25e57d2ecd5e95f36026b36e7a49f5a6d4ca6297710`
- waypoint SHA-256: `681b75668fcc47596731417292b841b2df141127bb4dc65cba8c848e9fc1eebe`
- PCD SHA-256 severities 1--5:
  `9fe1a9b7ddbe28d414f24e8816758478be919119df92214a0503aa7a4432d223`,
  `4305a63dc7081d3739f8edb6597c5d6e45932feb491e4306af9b25b5c5f7c1e3`,
  `29dcb80bc6c3367dda7cc5e2e560dd79f0bf8cda92c837046105fca2868c46a4`,
  `677b5cd7ab44518d34f0a3b214e7434e6579d57560657554d9892dcb4004d61b`,
  `08954c91966bd83a27c56b721b2ea268cc345420cda560f97374635c8a72ecf3`.

## Registered calibration outcome

The frozen 15-row smoke completed in 21.6 minutes.  All rows were unique,
first-attempt and quality-valid, with zero authoritative contact.  Full and
Adaptive were 5/5 safe; Sector was 4/5 safe.  The sole Sector timeout occurred
before the critical hazard turn.  Adaptive future-trajectory risk braking was
present in only 2/5 rows.  Both the 4/5 Adaptive-delivery condition and the
2/5 Sector-degradation condition failed, so the registered decision is
`STOP_CALIBRATION_GATE_FAILED`.  No independent maps or 150-row evaluation
were launched.  The probe also overlapped the upper wall and is excluded from
visibility conclusions.  See
`docs/angular_blind_turn_calibration_result_20260908.md` for the audit and
root-cause analysis.
