# Scenario7 stopped-departure v4 functional smoke

Status: G1 Full functional smoke and fresh three-mode n=1 gate completed. The
candidate remains opt-in/default-off and is not promoted to a stable or
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

## Fresh G1 three-mode gate

The next gate was run from the repository root without retry at
`results/scenario7_stopped_departure_v4_g1_triplet_20260927/`. It completed all
three planned modes and generated all summaries. Every source-contract and
small-pool timing check passed.

| Metric | Full | Fixed Sector | Adaptive |
|---|---:|---:|---:|
| Completion | 5/5 | 2/5 | 5/5 |
| Safety contacts | 0 | 1 | 0 |
| Mission time (s) | 47.61 | 180.01 | 55.00 |
| Minimum body clearance (m) | 0.272 | -0.057 | 0.280 |
| Mean end-to-end CPU (cores) | 0.7415 | 0.3128 | 0.4954 |
| End-to-end CPU (core-s) | 38.5509 | 57.5709 | 29.1214 |
| Sensor payload (MiB/s) | 10.2660 | 4.2830 | 3.6637 |
| Algorithm delivery (MiB/s) | 10.9701 | 8.7161 | 7.5263 |
| Map update (ms/frame) | 31.6701 | 6.3570 | 11.7554 |

Adaptive opened effective Full six times and closed six times. All six refresh
requests received committed acknowledgements; Full-open time duty was11.796%
and point duty31.858%. It recovered the Sector failure while retaining lower
cost than Full: mean end-to-end CPU -33.18%, algorithm mean CPU -35.55%, sensor
payload -64.31%, algorithm-delivery payload -31.39% and map-update time -62.88%.

The complete engineering objective is **not** passed: Adaptive took15.52%
longer than Full, so end-to-end cumulative CPU fell only24.46%, below the30%
target, and the mission-time guardrail failed. These are exploratory n=1 values,
not confidence bounds. Across the triplet,21 staged certificates produced21
releases and every logged P/V/A release error was exactly zero.

## Fresh G4 three-mode gate

The conditional G4 gate ran without retry at
`results/scenario7_stopped_departure_v4_g4_triplet_20260927/`. All modes
completed 5/5 waypoints with zero contact, and all source-contract and
small-pool timing checks passed.

| Metric | Full | Fixed Sector | Adaptive |
|---|---:|---:|---:|
| Completion | 5/5 | 5/5 | 5/5 |
| Safety contacts | 0 | 0 | 0 |
| Mission time (s) | 55.61 | 48.78 | 53.23 |
| Minimum body clearance (m) | 0.246 | 0.303 | 0.303 |
| Mean end-to-end CPU (cores) | 0.7698 | 0.4819 | 0.5046 |
| End-to-end CPU (core-s) | 46.4796 | 25.4017 | 28.7129 |
| Sensor payload (MiB/s) | 10.5061 | 2.8655 | 3.4415 |
| Algorithm delivery (MiB/s) | 11.3054 | 6.0541 | 7.1685 |
| Map update (ms/frame) | 30.7111 | 10.4356 | 11.5568 |

Adaptive opened and closed Full three times, with three committed refresh ACKs.
Versus Full it reduced mean end-to-end CPU 34.44%, cumulative CPU 38.22%, sensor
payload 67.24%, algorithm-delivery payload 36.59% and map-update time 62.37%,
while finishing 4.28% faster. This passes the measured n=1 engineering
thresholds, but the controller correctly leaves `target_met=false` because the
profiled exploratory observation still requires an unprofiled confirmation.
Across the triplet, 20 certificates produced 20 releases and every P/V/A
release error was zero. G4 does not show Sector degradation and cannot by itself
support the intended safety-superiority claim.

## Urban three-mode gate and retained failure

Because G4 passed the conditional gate, Urban ran once without retry at
`results/scenario7_stopped_departure_v4_urban_triplet_20260927/`.

| Metric | Full | Fixed Sector | Adaptive |
|---|---:|---:|---:|
| Completion | 5/5 | 0/5 | 0/5 |
| Safety contacts | 0 | 0 | 0 |
| Mission time (s) | 63.68 | 180.01 | 180.00 |
| Path length (m) | 267.514 | 5.113 | 5.105 |
| Minimum body clearance (m) | 0.489 | 0.162 | 0.061 |
| Mean end-to-end CPU (cores) | 0.8418 | 0.3050 | 0.4853 |
| End-to-end CPU (core-s) | 57.7226 | 56.4970 | 89.6809 |

Full completed safely. Sector and Adaptive both stopped before waypoint 1 and
timed out. Adaptive's 42.35% lower mean CPU is not an admissible performance
success: its 2.83x mission time raised cumulative CPU by 55.37%. Its Full view
opened once, received its committed map ACK, never closed, and occupied 95.264%
of wall time / 99.498% of points. Thus the failure is not a missing Full-open
event or missing refresh ACK.

The exact sequence is deterministic in the retained trace. Initial stopped
departure certification/release succeeded at generation 1/map 76 with zero
P/V/A error, followed by six normal commits and about 5.1m of motion. At
6.85m/s the guard detected an occupied trajectory point with TTC 0.015s and
correctly entered fail-closed stop. The perfect-drone model then held position
`(-3.742,3.416,2.067)` but continued publishing the last commanded odometry
twist of 6.851m/s. The independent position-difference estimator correctly
reported zero speed, so the stale twist did not create a false moving brake.

After 0.25s of physical stability, however, strict stationary validation still
returned `UNOBSERVED`. Its existing unknown-relaxed recheck accepted only
`SAFE`; at this pose the raw body was clear by 0.061m but the larger planning
inflation returned `CLEARANCE_MARGIN`. That combination was not admitted, so
1,663 bounded brake retries stayed fail-closed, no emergency recovery was
dispatched, and the already-open Full view could not help. This is a stationary
hold recertification branch gap, separate from the v3/v4 departure continuity
bug. It must be fixed with a full-query soft-margin completion proof rather
than by changing the map, mission, radius or timeout.

## Current decision

v4 remains default-off and is **not promoted**. It repairs the deterministic
departure discontinuity and passes G1/G4 functional gates, but Urban exposes a
new, narrower post-stop liveness defect. Do not start repetitions or the
seven-map campaign. The next bounded candidate should revalidate a physically
stable hold with `DeferSoftMarginUntilHardChecksComplete`, accept a relaxed
`CLEARANCE_MARGIN` only when every hard query and final map/deadline check has
completed, then rerun Urban Adaptive first. Preserve all v4 results unchanged.
