# Map9--10 static three-mode n=30 preregistration

Date frozen: 2026-09-07 (Asia/Seoul), before the first campaign row

## Question and scope

This campaign measures repeated execution reliability and computation on the
existing, pre-positioned static Map9 and Map10 environments.  It does not use
side-entry obstacle injection.  These two maps are a deliberately selected
hard-map stress subset, not an unseen-map generalization set.

The frozen cohort is 2 maps x 3 modes x 30 runs = 180 unique rows.  Mode order
rotates by run so every mode occupies each order position ten times per map.
The authoritative contact oracle is the common unfiltered source PCD with a
0.20 m vehicle sphere; the legacy live-cloud `collisions` field is not used as
the safety endpoint.

## Frozen treatment

- Maps: `seed9`, `seed10`.
- Modes: `full`, `sector`, `adaptive`.
- Planner speed/profile: v7, 45-degree Sector/Adaptive half-angle.
- Full input: integrated unmodified `/cloud_registered` handoff.
- Sector input: fixed 45-degree C++ sensor-frontend filtering.
- Adaptive input: the same 45-degree frontend plus the frozen risk-enforced
  bounded Full-opening policy.
- Loop timeout: 180 s.
- Resource guard, cgroup CPU accounting, optimizer-phase memory trace and
  reliable filtered map link remain enabled.
- No planner, filter, map, waypoint or threshold is changed between rows.

The exact command is:

```bash
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 scripts/native_campaign/native_campaign.py \
  --maps seed9 seed10 \
  --modes full sector adaptive --runs 30 --rotate-modes \
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
  --artifacts-dir results/map9_10_static_three_mode_n30_artifacts_20260907 \
  --out results/map9_10_static_three_mode_n30_raw_20260907.csv
```

## Frozen success, interruption and restart rules

For Full and Adaptive, a protected-mode failure is either:

1. `success != true`, meaning all five loop waypoints were not reached within
   the mission contract; or
2. authoritative `safety_collisions > 0` or `static_pcd_collisions > 0`.

On the first protected-mode failure, the campaign is stopped after preserving
the complete row and per-attempt artifacts.  The failed row is not replaced by
a successful retry.  Cause analysis must distinguish planner behavior from
startup, process, resource, measurement and host failures.  Any necessary fix
is followed by targeted regression tests and a small reproduction.  The full
180-row confirmatory cohort is then restarted from run 1 under a new result
filename; pre-fix and partial rows remain diagnostic evidence and are not
pooled with the restarted cohort.

Sector failure does not stop the campaign because Sector is the fixed ablation
under observation.  An infrastructure abort/retry or invalid measurement in
any mode is recorded separately.  A final cohort is claimable only when all
180 keys are unique and all rows are first-attempt, run/resource/speed/
performance valid with zero retry, resource abort and OOM count.  If a
preflight resource timeout occurs before a row, no row is manufactured; the
host problem is corrected and the cohort restarts unless no flight row has yet
been recorded.

## Frozen reporting

Report per map and mode: completion count, contact-run/event count, mean and
minimum static clearance, mean/SD mission time, Adaptive effective and
trajectory-guard Full openings, planner ingress, map compute per frame,
algorithm CPU, common end-to-end CPU/core-seconds, PSS, resource minima and
retry counts.  Report pooled Map9--10 values only in addition to, never instead
of, the per-map table.

Repeated executions on two selected maps estimate run-to-run reliability on
this stress subset; they are not 60 independent map samples.  If Full and
Adaptive both achieve 60/60 completion and zero contact, report the exact
binomial interval rather than a population-level 100% guarantee.  A Sector
contact difference is descriptive unless a prespecified paired binary test is
valid for the realized trial pairing.  No safety superiority is inferred when
Sector also has zero failures.

## Frozen identifiers

- `/root/super_ws/src/SUPER` base commit:
  `2ad3419c127a617c6d7df6925e81a14175a9c096` (working tree contains the
  already mirrored campaign implementation).
- Full config SHA-256:
  `6589b7c4065aa528facecc8f0f624c4f178718933afa537af861f4eb54cee540`.
- Sector config SHA-256:
  `eafae08a239cc4409b7df0b829f7951a0d26a0ea3ec5a97c3f03ad3a2b44eb24`.
- Adaptive config SHA-256:
  `82c8536181b1c402330d47a23c3b17311537f91105eca71337286d0d514277a7`.
- Campaign runner SHA-256:
  `a4d72ae82b8b30d90dc8ab19fe473cc3a847408c97f94e2eacd9cedb9d982eb2`.
- Loop monitor SHA-256:
  `a84d62214cd4c8e1cfdf863108b331315979a1d59e6eb745012f1f34d5a10c45`.
- Summarizer SHA-256:
  `61e3419314c93ad68725b79e6071840bfa264463b81f83686ececb5ef2911e3f`.
- Installed Full executable SHA-256:
  `1bad4a4f76e1dac3a73caa9f12aba8886f149131bf8a0c2d9cf5181ef245f19f`.
- Installed frontend executable SHA-256:
  `a0d8759b89ce25a0bf1949e40a548790de972eb3a8662c5e47e72a590b04b053`.
- Installed planner executable SHA-256:
  `7a7644354b5ec4a0b65ff2e1cec4fd943eb22067a7777fc3a24a33db441997fd`.
- Installed native filter executable SHA-256:
  `5487ef14344f37552d89a89c5810c5da6cef18d85e0c3749ba3f0e34a46016a0`.

At freeze time the host had about 9.54 GiB available memory, memory PSI
`some/full avg10=0`, about 180 GiB free disk and no live ROS/campaign process.
Host swap was almost saturated by external historical pages, but the prior
correct-deployment 300-row campaign established that per-campaign swap and
memory PSI, not the persistent host swap counter alone, are the validity
criteria.
