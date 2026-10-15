# Isolated angular blind-turn calibration result

Run: 2026-09-08 23:43 -- 2026-09-09 00:04 KST

Frozen design: `docs/isolated_angular_blind_turn_preregistration_20260908.md`

Decision: **`STOP_CALIBRATION_GATE_FAILED`**

## Outcome

The planner was not changed.  The separately named `abt2_cal_t1..t5`
calibration ran all preregistered 15 rows in 20.8 minutes.  All rows were
unique, first-attempt, run/resource/speed/performance/cgroup-valid.  There was
no retry, infrastructure failure, resource abort, OOM, static-PCD contact or
analytic-hazard contact.

| Map | aperture x | Full | Sector | Adaptive | Full / Sector / Adaptive time (s) | Adaptive exact risk brake | Adaptive Full transitions |
|---|---:|---|---|---|---:|---:|---:|
| t1 | 19.500 | complete, 0 contact | timeout after target, 0 | complete, 0 | 18.73 / 90.00 / 25.10 | 0 | 12 |
| t2 | 19.575 | timeout after target, 0 | timeout after target, 0 | timeout after target, 0 | 90.01 / 90.01 / 90.00 | 0 | 43 |
| t3 | 19.650 | timeout after target, 0 | timeout after target, 0 | complete, 0 | 90.01 / 90.01 / 73.69 | 0 | 10 |
| t4 | 19.725 | complete, 0 contact | timeout after target, 0 | complete, 0 | 38.53 / 90.00 / 19.05 | 0 | 3 |
| t5 | 19.800 | complete, 0 contact | timeout after target, 0 | timeout after target, 0 | 38.78 / 90.00 / 90.01 | 0 | 56 |
| **Total** | -- | **3/5 complete** | **0/5** | **3/5** | 55.21 / 90.00 / 59.57 mean | **0/5 rows** | **124** |

All failures reached the first target `(24,24)` and therefore occurred at or
after the intended turn.  Sector's 5/5 degradation condition passed, but Full
and Adaptive both missed the required 5/5 safe-completion condition.

## Frozen gate audit

| Condition | Result |
|---|---|
| exactly 15 unique rows | PASS |
| all rows first-attempt and quality-valid | PASS |
| Full safe completion 5/5 | **FAIL: 3/5** |
| Adaptive safe completion 5/5 | **FAIL: 3/5** |
| Adaptive exact fresh frontend future-risk brake >=4/5 | **FAIL: 0/5** |
| Sector degraded at/after target >=2/5 | PASS: 5/5 |
| isolated surface probe seen outside Sector 10/10 | **FAIL: 6/10** |

The gate was evaluated as preregistered.  No favourable aperture was selected,
no independent maps were generated, and the contingent 150-row evaluation was
not run.  No McNemar or significance test is reported for this n=1 mechanism
calibration.

## Why the offline geometry did not transfer to closed-loop flight

The structural validator was internally correct for its stated assumptions:
an origin fixed on `x=24`, northbound line of sight, the actual 151-point
cylinder lattice, finite 0.30 m wall thickness and 0.38 m aperture.  It found
47.145--50.596 degree first-surface rays and 0.422--0.529 s to the nominal
waypoint-switch boundary at 7 m/s.

Those assumptions did not describe the realised sensing state:

1. The vehicle approached with `x=24.28..25.46` at the first recorded patch,
   rather than exactly `x=24`.  A narrow aperture is highly sensitive to this
   lateral error.
2. SUPER began curving and rotating before the waypoint switch.  At probe
   arrival, body-relative angles ranged from 4.8 to 51.2 degrees and the
   filter's actual centre classified four of ten filtered rows inside 45
   degrees.
3. The selected isolated patch was on the north/east exposed surface around
   `(17.0,25.3)`, not on the surface intersecting the nominal westbound path
   near `y=24`.  Seeing that patch does not imply a collision within the
   frontend's 1 s trajectory horizon.
4. A geometric line of sight to one PCD surface sample does not guarantee that
   the 0.4-degree simulated LiDAR ray lattice returns it at the same pose.
   Actual probes arrived around `y=22.71..23.26`, after the predicted
   `y=18.80..19.55` interval.

The isolated probe itself was valid: it was observed in 10/10 filtered rows
and cannot overlap either wall.  The failure is therefore a modelling gap
between static line-of-sight validation and realised raycast/trajectory
dynamics, not the v1 wall-contamination bug.

## Why Adaptive's future-trajectory guard did not fire

The C++ frontend was alive and correctly configured.  Per Adaptive row it
received 34--68 trajectory messages, produced 117--472 trajectory-risk
verdicts at about 5 Hz, and computed each verdict in 2.56--5.77 ms on average.
However, `risk_occupied_verdicts=0` in all five rows.  Consequently the planner
recorded zero enforced occupied verdicts and zero frontend risk brakes.

The 124 Adaptive effective-Full transitions were caused by existing replan or
ordinary trajectory-guard recovery, not by the raw-window future-trajectory
mechanism.  They must not be relabelled as evidence that the proposed hazard
detector worked.

The likely causal chain is: the aperture first reveals a non-conflicting
hazard surface; by the time trajectory-conflicting surfaces are available,
the ordinary planner has already stopped, changed trajectory or opened a Full
refresh.  The frontend then evaluates a stopped/avoiding candidate and
correctly returns CLEAR.

## Timeout mechanism

This fixture also proved too hard for the frozen Full planner.  The two Full
timeouts repeatedly entered topology reroute after reaching the target:

- t2: 105 reroute arms, 347 searches, repeated A* `NO_PATH` and optimisation
  overtime near `(18.1,24.9)`;
- t3: 107 arms, 336 searches, repeated `PlanFromRest` failures near
  `(19.6,25.3)`.

The two Adaptive timeouts show the same failure family:

- t2: 125 arms, 442 searches, 725 frontend-observed replan failures and CIRI
  infeasibility near `(20.6,23.7)`;
- t5: 126 arms, 390 searches, 697 replan failures and repeated A* `NO_PATH`
  near `(22.6,23.8)`.

Sector failed 5/5 after the target.  It either exhausted topology searches or,
in t1, stopped after the filtered map ceased committing and entered the
existing `MAP_STALE` fail-closed loop.  The analytic +0.45 m body-clearance
bypass was therefore not a sufficient planner-feasibility certificate: it
omitted ROG inflation, discrete search bounds, local planning horizon,
trajectory dynamics and the accumulating reroute exclusion zones.

The mixed Full sequence `complete, timeout, timeout, complete, complete`
despite only a 7.5 cm aperture shift also shows that this narrow-aperture
fixture is timing-sensitive.  It is not suitable for a confirmatory paper
comparison.

## Computation (calibration-only)

| Mode | ingress MiB/s | map compute ms/frame | algorithm cores | common E2E cores | common E2E core-s | peak PSS MiB |
|---|---:|---:|---:|---:|---:|---:|
| Full | 11.991 | 12.906 | 1.227 | 1.283 | 74.361 | 3394.0 |
| Sector | 0.928 | 5.394 | 0.292 | 0.557 | 50.997 | 3326.1 |
| Adaptive | 2.910 | 9.510 | 0.898 | 1.202 | 74.523 | 3470.9 |

Adaptive versus Full reduced ingress 75.73%, map compute 26.32%, algorithm
cores 26.81% and E2E mean cores 6.27%, but did not reduce E2E core-seconds
(-0.22%) or peak PSS (-2.27%).  These are diagnostic calibration numbers, not
paper efficiency evidence, because modes did not complete the same missions
and timeout durations dominate exposure.

System swap remained almost full (2047.59--2048.00 MiB), but campaign cgroup
swap stayed about 738.5--738.7 MiB, memory PSI maxima were zero, every row was
resource-valid, and OOM delta was zero.  There is no measured infrastructure
or resource failure explaining the completion pattern.

## Decision and next admissible step

Stop this experimental branch at calibration.  Repeating this fixture or
moving another aperture by centimetres would be post-result tuning and would
not establish the target mechanism.

Before any v3 flight, build a deterministic replay/kinematic witness test that
uses the simulator's actual LiDAR raycast and the frontend's actual crop/risk
code.  It must demonstrate, for a frozen sequence of poses and committed
trajectories, all of the following before a planner is introduced:

1. a trajectory-conflicting hazard patch is present in raw input;
2. the same patch is absent from fixed Sector input;
3. the frontend produces an exact fresh `OCCUPIED` verdict in at least two
   consecutive 5 Hz periods;
4. a separately checked, inflation-aware A* corridor is feasible for Full.

Only after that witness passes should a new closed-loop calibration family be
preregistered.  The preserved Map1--10 and `occ_bw` results remain the current
paper evidence; `abt_cal` and `abt2_cal` are negative mechanism-development
records.

## Reproducibility files

- raw: `results/isolated_angular_blind_turn_three_mode_n1_raw_20260908.csv`
- gate/validation: `results/isolated_angular_blind_turn_three_mode_n1_{gate,validation}.json`
- tables: `results/isolated_angular_blind_turn_three_mode_n1_{summary,reductions,map_table}.csv`
- generator/validator/analyzer:
  `scripts/native_campaign/{gen,validate,analyze}_isolated_angular_blind_turn_calibration.py`
- raw run artifacts are retained locally under
  `results/isolated_angular_blind_turn_three_mode_n1_artifacts_20260908/` and
  intentionally excluded from Git because they are 19 MiB of reproducible
  stack/performance traces.
