# 90-degree angular blind-turn calibration result

Date: 2026-09-08 (Asia/Seoul)

## Decision

`STOP_CALIBRATION_GATE_FAILED`

The 15 preregistered calibration rows are structurally and operationally
valid, but the mechanism gate failed.  Full and Adaptive were both 5/5 safe.
Fixed Sector was degraded in only 1/5 rows rather than the required 2/5, and
the Adaptive raw-window future-trajectory brake occurred in only 2/5 rows
rather than 4/5.  Therefore no independent maps were generated and the
planned 150-row evaluation was not launched.

This is a negative calibration result, not a planner failure and not evidence
that Adaptive is less safe than Sector.  All 15 rows had zero authoritative
contact.

## Map-by-map result

| map | hazard r | Full | Sector | Adaptive | time F/S/A (s) | hazard clearance F/S/A (m) | Adaptive risk brake | Adaptive Full opens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| abt_cal_s1 | 1.10 | 6/6, 0 contact | 6/6, 0 | 6/6, 0 | 58.04 / 81.85 / 57.43 | +1.481 / +0.586 / +0.812 | 0 | 23 |
| abt_cal_s2 | 1.20 | 6/6, 0 | 1/6 timeout, 0 | 6/6, 0 | 63.21 / 210.00 / 59.76 | +1.219 / +16.928 / +1.622 | 0 | 23 |
| abt_cal_s3 | 1.30 | 6/6, 0 | 6/6, 0 | 6/6, 0 | 57.67 / 57.90 / 60.60 | +0.978 / +0.711 / +2.442 | 1 | 25 |
| abt_cal_s4 | 1.40 | 6/6, 0 | 6/6, 0 | 6/6, 0 | 59.27 / 68.65 / 60.46 | +1.505 / +0.358 / +0.978 | 1 | 10 |
| abt_cal_s5 | 1.50 | 6/6, 0 | 6/6, 0 | 6/6, 0 | 61.07 / 58.07 / 58.35 | +0.754 / +0.767 / +1.402 | 0 | 24 |

`s2` Sector's +16.928 m hazard clearance is not a superior avoidance result:
the vehicle never reached the critical hazard.  It stopped at `(24.269,
6.596)` after reaching only the first waypoint.

## Preregistered gate

| condition | required | observed | result |
|---|---:|---:|---:|
| exact unique and quality-valid rows | 15/15 | 15/15 | pass |
| Full contact-free completion | 5/5 | 5/5 | pass |
| Adaptive contact-free completion | 5/5 | 5/5 | pass |
| Adaptive `frontend_risk_brake_events > 0` | at least 4/5 | 2/5 | **fail** |
| Sector incomplete/contact | at least 2/5 | 1/5 | **fail** |
| Sector degradation at/after critical turn | diagnostic | 0/5 | mechanism not delivered |

Every row was first-attempt, run/resource/speed/performance/cgroup-valid, with
zero retry, infrastructure failure, resource abort and OOM delta.  The
preflight threshold amendment affected only the wait-before-launch threshold;
runtime memory/PSI gates remained enabled and passed.

## Why the gate failed

### 1. The channel did not consistently force a Sector failure

Four Sector rows passed the critical channel contact-free.  Their minimum
hazard body clearance was +0.358 to +0.767 m.  Once the hazard entered the
45-degree crop, the unchanged planner still had enough open topology to pass
north of it.  Increasing cylinder radius was therefore not a monotone control
of the intended angular-blind mechanism.

The only Sector timeout, `abt_cal_s2`, was not caused by the north-east
hazard.  The vehicle completed the eastbound first leg, turned north and then
stopped around `y=6.6 m`, before the critical `(24,24)` waypoint.  The C++
frontend continued to receive and publish at about 10 Hz, but retained only
1.386% of input points.  The planner repeatedly logged `Empty or non-dense
point cloud`; ROG-Map stopped at version 85, the guard observed map age 0.558 s
against the 0.550 s limit, entered fail-closed `EMER_STOP`, and map age then
grew beyond 200 s.  This is a real fixed-sector/map-readiness liveness
failure, but it is an earlier-turn/background confound and cannot be
attributed to the test hazard.

### 2. Adaptive often avoided the hazard before the raw risk verdict became causal

Only s3 and s4 emitted a fresh exact-generation
`[FRONTEND_RISK_ENFORCE] action=BRAKE`.  In s4 it directly produced a safe
0.529 s brake.  In s3 it triggered fail-closed handling; the first moving
brake candidate was dynamically invalid, and a later stopped retry was safe.

In s2, the frontend did calculate fresh `OCCUPIED` verdicts, but the planner
had already entered emergency handling due to its ordinary pre-commit guard;
the verdict was later stale/generation-mismatched and was not counted as a
causal risk brake.  s1 and s5 used ordinary candidate rejection/topology
reroute paths without a frontend risk-brake event.  Thus Adaptive was safe,
but the specific raw-window mechanism was neither necessary nor consistently
delivered by this geometry.

The geometric reveal-to-waypoint-switch interval was also short: roughly
0.9--1.0 m at a measured 5--6.5 m/s, comparable to one or two 10 Hz sensor
frames and only about one 5 Hz risk-evaluation period.  That explains the
non-deterministic 2/5 delivery better than hazard radius does.

### 3. The raw static probe is contaminated

The runner used a circle centred on the hazard with radius `hazard_r+0.05`.
The upper wall's nearest surface is only 1.05 m from that centre, so every
probe overlaps the wall.  For example, s1 Sector reported its first probe at
`y=13.21 m`, far before the validator's hazard-surface reveal.  These probe
fields cannot identify first hazard visibility and are excluded from all
conclusions.  This measurement defect did not alter a point cloud, planner
decision, success/contact result, or the formal gate, but it must be corrected
before another map version.

## Calibration-only computation result

The values below are descriptive n=1 means, not inferential results and not a
replacement for the existing n=10 efficiency evidence.  Sector's 210 s
timeout also depresses its CPU/core-second averages.

| metric | Full | Sector | Adaptive | Adaptive reduction vs Full |
|---|---:|---:|---:|---:|
| mission time (s) | 59.852 | 95.294 | 59.320 | 0.889% |
| planner ingress (MiB/s) | 4.584 | 0.760 | 0.806 | 82.425% |
| map compute (ms/frame) | 42.984 | 10.045 | 21.974 | 48.879% |
| algorithm CPU (mean cores) | 1.617 | 0.903 | 1.101 | 31.949% |
| common E2E CPU (mean cores) | 1.677 | 1.152 | 1.399 | 16.561% |
| common E2E core-seconds | 103.326 | 87.938 | 85.727 | 17.033% |
| common E2E peak PSS (MiB) | 3467.338 | 3403.140 | 3428.750 | 1.113% |

Adaptive produced 105 effective Full-open transitions across five rows.  The
sensor input rate remained approximately 10 Hz.  No McNemar test is run: this
is a five-cell calibration, the preregistered gate failed, and the sole binary
discordance did not occur at the intended hazard.

## Next experimental revision

Do not tune or modify the planner based on this outcome.  A new map version
should change the experimental fixture instead:

1. start at `(24,0)` facing north, so the hazard corner is the first and only
   evaluated turn and the s2 early-turn confound is impossible;
2. use one common empty/controlled background during calibration, rather than
   changing background and hazard radius together;
3. expose an isolated patch on the hazard surface to the raw probe so a wall
   cannot satisfy it;
4. increase raw reveal-to-switch time to at least 0.4 s while keeping the full
   hazard silhouette outside 45 degrees, guaranteeing at least two 5 Hz risk
   opportunities;
5. require every Sector-bad event to occur after the critical waypoint, and
   require a fresh exact-generation Adaptive risk brake before any independent
   evaluation.

This must use a new family name and a new preregistration.  The present
`abt_cal` rows remain a complete negative calibration and are never pooled.

## Evidence

- preregistration:
  `docs/angular_blind_turn_calibration_preregistration_20260908.md`
- raw rows:
  `results/angular_blind_turn_calibration_three_mode_n1_raw_20260908.csv`
- audit/gate:
  `results/angular_blind_turn_calibration_three_mode_n1_{validation,gate}.json`
- summaries:
  `results/angular_blind_turn_calibration_three_mode_n1_{summary,reductions,map_table}.csv`
- analyzer:
  `scripts/native_campaign/analyze_angular_blind_turn_calibration.py`

Large per-run logs and traces remain local under
`results/angular_blind_turn_calibration_three_mode_n1_artifacts_20260908/` and
are intentionally not committed.
