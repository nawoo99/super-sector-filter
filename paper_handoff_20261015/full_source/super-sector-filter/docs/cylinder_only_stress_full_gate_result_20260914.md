# Cylinder-only Stress 1--5 Full feasibility result

Date: 2026-09-14 (Asia/Seoul)

Decision: **`STOP_PAIRED_CAMPAIGN_FULL_FEASIBILITY_GATE_FAILED`**

## Outcome

The frozen cylinder-only family was run once per map in Full mode at 7 m/s.
All five retained rows were first attempts, measurement-valid,
resource-valid, speed-valid and contact-free. Stress 1--3 completed, but
Stress 4--5 timed out before reaching the first loop waypoint. Completion was
therefore 3/5 (60%) and the preregistered Full feasibility gate failed.

| Map | Radius, m | Full result | Time, s | Waypoints | Contacts | Minimum static-PCD surface clearance, m | Final XY, m |
|---|---:|---|---:|---:|---:|---:|---:|
| Stress 1 | 0.150 | Complete | 82.30 | 5/5 | 0 | 0.430 | (1.122, -0.966) |
| Stress 2 | 0.275 | Complete | 72.11 | 5/5 | 0 | 0.340 | (1.115, -0.908) |
| Stress 3 | 0.400 | Complete | 85.15 | 5/5 | 0 | 0.274 | (1.088, -0.879) |
| Stress 4 | 0.525 | Timeout | 180.01 | 0/5 | 0 | 0.261 | (20.847, 19.999) |
| Stress 5 | 0.650 | Timeout | 180.01 | 0/5 | 0 | 0.592 | (19.999, 19.999) |

This is a valid negative feasibility result, not evidence that Full collided.
The safety count is 0/5 contacts, but completion is not acceptable for the
planned comparison. Consequently no Sector or Adaptive closed-loop flight was
run on these final names.

## Failure mechanism

The error is in the map certification logic, not in the Adaptive algorithm.
The structural gate certified a northern bypass from the first corner after
the turn. It did not certify the inbound diagonal from the origin to that
corner. The inner row of cylinders crosses this inbound route, so the vehicle
must solve an additional topology change before waypoint 1.

Stress 4 stopped at approximately `(20.85,20.00)` m. Its log contains 1,676
0.1 s A-star `TIME_OUT` results and 1,678 `PlanFromRest` failures. Stress 5
stopped near `(20.00,20.00)` m and cycled through 322 A-star timeouts, 488
replan-overtime events, 122 EXP optimizer failures (`ret=-1008`) and 203
trajectory-reroute arms. It did not escape within 180 s.

The severity sweep also unintentionally changed compute load. Because PCD
surface sampling density was fixed while radius increased, mean points per
input scan rose from 16.3k in Stress 1 to 33.8k/33.2k in Stress 4/5; planner
ingress rose from 5.07 to 10.38/10.17 MiB/s. Thus the last tiers combine
geometric difficulty with a fixed 0.1 s search-budget bottleneck. They are not
a clean radius-only safety comparison.

| Map | Mean input points/scan | Planner ingress, MiB/s | Mean algorithm CPU, cores | A-star timeout count |
|---|---:|---:|---:|---:|
| Stress 1 | 16,307 | 5.07 | 1.265 | 81 |
| Stress 2 | 20,262 | 6.30 | 1.343 | 47 |
| Stress 3 | 24,752 | 7.64 | 1.419 | 105 |
| Stress 4 | 33,792 | 10.38 | 1.421 | 1,676 |
| Stress 5 | 33,153 | 10.17 | 1.499 | 322 |

## Measurement-layer correction before the gate

The first launch attempt exposed a separate monitor defect before any mission
result existed. The new PCDs declare `FIELDS x y z intensity`, whereas the
static collision monitor flattened every numeric column and forced a
three-column reshape. It crashed before odometry collection on Stress 1 and
2. Those two non-results are preserved in
`results/cylinder_only_stress_full_feasibility_n1_infrastructure_aborted_20260914.csv`
and are not part of the five-row gate.

The monitor now resolves x/y/z column indices from the PCD `FIELDS` and
`COUNT` headers, ignores extra fields and fails closed on missing or non-finite
coordinates. Five loader tests plus the campaign/geometry tests passed before
the clean gate was restarted from Stress 1. No map or planner parameter was
changed between the aborted measurement initialization and the retained
flights.

## Integrity and resources

- Attempts: exactly one retained attempt per map; zero retries.
- Infrastructure failures: 0/5 retained rows.
- Speed-valid and resource-valid: 5/5.
- Static-PCD contacts: 0/5.
- Host swap was already essentially full (about 2,048 MiB) throughout.
  Minimum `MemAvailable` was 3,705 MiB in Stress 5, with memory PSI `some/full
  avg10` peaking at only 0.18, below the registered limits; no retained row was
  invalidated by resource pressure.

## Next admissible action

Keep these five frozen maps and this failure as development evidence. Do not
repair them under the same names and do not use them for a Sector-versus-
Adaptive claim. A new cylinder-only v2 family, if requested, should be newly
named and must add two pre-flight gates:

1. inflation-aware, local-horizon route certification from the origin through
   the inbound side of waypoint 1 and through the post-turn bypass; and
2. point-budget normalization across radius tiers so severity does not double
   planner ingress.

Only if all five new Full first-attempt flights complete without contact should
a small paired Sector/Adaptive pilot begin.

Machine-readable evidence:

- `results/cylinder_only_stress_full_feasibility_n1_raw_20260914.csv`
- `results/cylinder_only_stress_full_feasibility_n1_gate_20260914.json`
- `results/cylinder_only_stress_full_failure_forensics_20260914.json`
- `results/cylinder_only_stress_full_feasibility_n1_artifacts_20260914/`

