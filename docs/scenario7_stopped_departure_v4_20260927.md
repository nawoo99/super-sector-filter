# Scenario7 stopped-departure v4 functional smoke

Status: G1 Full functional smoke passed; broader validation has not started.
The candidate remains opt-in/default-off and is not promoted to a stable or
population-safe planner.

## Why v3 could not leave the start

The preserved v3 Full run timed out at 180.01 s with 0/5 waypoints, no motion,
no PositionCommand publication and 1,362 `POSITION_DISCONTINUITY` rejections.
Two independent defects were present:

1. `PlanFromRest` replaced the physical held point with a 0.05 m voxel centre.
   At `(0,0,1.5)` this imposes a theoretical minimum displacement of
   `sqrt(3)*0.025 = 0.043301 m`, already far above the unchanged 1 mm handoff
   tolerance. The observed minimum was 0.043510 m.
2. The candidate clock started when solving began, while release occurred
   later. Sampling that stale clock produced nonzero departure velocity and
   acceleration even though odometry remained stationary.

Changing only the timestamp or loosening the tolerance would not repair both
defects. The original v3 run and its failure classification remain unchanged.

## Bounded v4 implementation

The implementation is enabled only by the exact environment opt-in
`SUPER_STOPPED_DEPARTURE_V4=1`; the default is false. It makes no map, mission,
radius, speed, CIRI or guard-margin change.

- The actual held odometry point is the optimizer boundary. A nearby free voxel
  is only the discrete search seed, and the physical-to-search connector remains
  part of the guide/corridor.
- A stopped candidate is staged with exact generation, map version, command
  identity and a full safety certificate beginning at relative time zero.
- The same release function is used by ordinary async generation and certified
  emergency recovery. It rejects generation/map/trajectory/PVA mismatch and
  rebases position, yaw, EXP, backup boundaries and initial-egress receipt to one
  release wall time.
- Publication is prepared first, then certificate/identity are checked under the
  final locks; release occurs immediately before publishing the matching message.
  A rejected release remains held.

The source marker is:
`[STOPPED_DEPARTURE_V4] enabled=true physical_origin=true prefix_from_zero=true shared_release=true default_off=true`.

## Build and offline verification

All affected packages were built serially in the separate prefix
`/root/super_ws/scenario7_guard_v4_20260926/install`; original and v1-v3
installations were not overwritten. The final integrated
`perfect_drone_full_node` differs from the preserved v3 executable.

- planner CTest: 4/4 passed, including the new clock-rebase test;
- new v4 source-contract tests: 5/5 passed;
- inherited async source-contract tests: 12/12 passed;
- wrapper byte-compilation and `--help`: passed;
- all nine v4 runtime/mirror pairs: SHA256-identical.

The first two launch admissions did not start a flight: the first correctly
rejected stale v3 static-preflight bindings and the second exposed a missing
`rog_map` artifact in the new overlay. `rog_map` was built into the v4 prefix.
A third preflight exposed a missing `SOURCE` binding in the v4 child and was
fixed before the functional flight. These are infrastructure/admission outcomes,
not planner failures or successful trials.

## G1 Full functional smoke

Result directory:
`results/scenario7_stopped_departure_v4_g1_full_20260927_r2/`.

| Metric | Result |
|---|---:|
| Completion | 5/5 waypoints, success |
| Mission time | 53.69 s |
| Safety/static-PCD contacts | 0 / 0 |
| Minimum point distance / body clearance | 0.467 / 0.267 m |
| Maximum odometry speed | 7.001798 m/s |
| Speed bound | 7.0 + 0.01 m/s, passed |
| Stopped-departure certificates / releases | 8 / 8 |
| Ordinary / emergency certificates | 2 / 6 |
| Maximum release P/V/A error | 0 / 0 / 0 |

The initial ordinary release used generation 1 and map version 62. The same
release contract was subsequently exercised by certified emergency recovery,
so this Full run covered both call sites. Full-source 360-degree acquisition,
near-range async startup identity and the inherited strict recovery audit all
passed. This resolves the deterministic v3 no-command/no-motion symptom in this
one functional run; it is not a claim of repeatability or population safety.

The flight itself completed, but the optional CPU postprocessor then resolved a
relative performance-CSV path from `/root/super_ws` rather than the repository
root. The campaign status is therefore honestly preserved as
`STOPPED_FOR_DIAGNOSIS`; no replacement flight was run. The raw row reports
0.754486 algorithm cores / 43.788173 core-s and 0.802665 end-to-end cores /
46.584326 core-s, but a Full-only n=1 diagnostic is not an admissible CPU
comparison. A compact statement of the distinction is in
`flight_evidence_summary.json` in the result directory.

## Next gate

Run a fresh G1 Full/Sector/Adaptive n=1 from the repository root so the
postprocessor completes, retaining every failure without retry. If all source,
timing, safety and completion gates pass, expand to G4 and Urban before any
larger seven-map or repeated campaign. No result from this smoke should be
pooled with v2/v3 or the established Normal tables.
